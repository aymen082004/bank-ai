# @tool
# def call_subagent(agent_name: str, task_description: str) -> str:
#     """
#     Call a specialized subagent to handle a specific task.

#     Available agents:
#     - reception: Customer Q&A, account opening, balance verification
#     - credit: Credit file analysis, credit scoring
#     - commercial: Customer profile analysis, product recommendation
#     - signature_checks: Signature and check verification
#     - fraud_detection: Transaction analysis, fraud classification
#     - analysis_reporting: Agency activity analysis, KPI tracking
#     - recovery: Unpaid loan monitoring, customer follow-up

#     Args:
#         agent_name: Name of the subagent (e.g., 'reception', 'credit').
#         task_description: Clear description of what the agent should do.

#     Returns:
#         The result from the subagent as a string.
#     """
#     try:
#         result = dispatch(agent_name, task_description)
#         return result
#     except Exception as e:
#         return f"Error calling {agent_name}: {str(e)}"

from __future__ import annotations

import json
import os
import re
import sys
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Any, List
# from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_ollama import OllamaEmbeddings, ChatOllama
from db.mcp_handler import mcp_handle
from dotenv import load_dotenv
import chromadb

dotenv_path = Path(__file__).resolve().parents[1] / ".env"
if not dotenv_path.exists():
    dotenv_path = Path(__file__).resolve().parents[2] / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()


def _get_chroma_client():
    chromadb_dir = Path(__file__).parent / "ressources" / "chromadb"
    return chromadb.PersistentClient(path=str(chromadb_dir))


def _suggest_booking_slots_local(user_id: str = None) -> list[tuple]:
    """
    Enhanced booking slot suggestion function with calendar checking.
    Returns available booking slots for the next 7 days.
    """
    from datetime import datetime, timedelta, time
    from db.mcp_handler import google_auth_db

    now = datetime.now()
    slots = []

    user_calendar_events = []
    if user_id:
        try:
            # Get user from database to check calendar
            users_collection = google_auth_db["users"]
            user_doc = users_collection.find_one({"google_id": user_id})

            if user_doc and "calendar_events" in user_doc:
                user_calendar_events = user_doc["calendar_events"]
                # print(f"Found {len(user_calendar_events)} calendar events for user")  # DEBUG: Commented out
        except Exception as e:
            # print(f"Warning: Could not check user calendar: {e}")  # DEBUG: Commented out
            pass  # Add pass to complete the except block

    for day_offset in range(1, 8):  # Next 7 days
        day = now + timedelta(days=day_offset)
        # Skip weekends
        if day.weekday() >= 5:
            continue

        # Check if user has existing events on this day
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Check for conflicts with user's existing events
        has_conflict = False
        for event in user_calendar_events:
            if "start_time" in event and "end_time" in event:
                event_start = datetime.fromisoformat(event["start_time"])
                event_end = datetime.fromisoformat(event["end_time"])

                if not (event_end <= day_start or event_start >= day_end):
                    if not (event_start >= day_end or event_end <= day_start):
                        has_conflict = True
                        break

        if not has_conflict:
            morning_start = day.replace(hour=9, minute=0, second=0, microsecond=0)
            morning_end = morning_start + timedelta(hours=1)

            afternoon_start = day.replace(hour=14, minute=0, second=0, microsecond=0)
            afternoon_end = afternoon_start + timedelta(hours=1)

            slots.append((morning_start, morning_end))
            slots.append((afternoon_start, afternoon_end))

        if len(slots) >= 3:
            break

    return slots[:3]  # Return up to 3 slots


LLM = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
)


def _query_rag_store(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Query ChromaDB for relevant policy information."""

    try:
        client = _get_chroma_client()
        collection = client.get_or_create_collection(name="loi_2016_48")

        if collection.count() == 0:
            return [{"error": "RAG collection is empty"}]

        embeddings = OllamaEmbeddings(model="mxbai-embed-large:latest")
        query_vector = embeddings.embed_query(query)

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["documents", "metadatas"],
        )

        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        docs = []
        for i, doc_text in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            docs.append(
                {
                    "text": doc_text,
                    "metadata": metadata,
                }
            )

        return docs

    except Exception as e:
        print(f"RAG Error: {e}")
        return [{"error": str(e)}]
    except Exception as e:
        return [{"error": f"Failed to query RAG store: {str(e)}"}]


def _generate_hypothetical_document(query: str) -> str:
    """Generate a hypothetical document based on the query using HyDE approach."""
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.7,
    )

    system_prompt = """You are generating a hypothetical bank policy document that would be relevant to the user's query.
Write a concise, informative passage that contains the key information that would answer their question about banking policies, regulations, or procedures.
Write it as if it were an excerpt from an official banking policy document."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Query: {query}"),
    ]

    response = llm.invoke(messages)
    return response.content.strip()


def _rerank_documents(query: str, documents: List[dict]) -> List[dict]:
    """Rerank documents using local Qwen3-Reranker model via Ollama."""
    try:
        reranker = ChatOllama(
            model="dengcao/Qwen3-Reranker-0.6B:Q8_0",
            base_url="http://localhost:11434",
            temperature=0.1,
            format="json",
        )

        reranked_docs = []

        for doc in documents:
            prompt = f"""Please score the relevance of this document to the query on a scale of 0.0 to 1.0.
            
Query: {query}

Document: {doc["text"][:500]}...

Respond with JSON: {{"score": 0.95, "reasoning": "Highly relevant because..."}}"""

            try:
                response = reranker.invoke(prompt)
                if hasattr(response, "content"):
                    content = response.content
                    import re

                    score_match = re.search(r'"score"\s*:\s*([0-9.]+)', content)
                    if score_match:
                        score = float(score_match.group(1))
                    else:
                        number_match = re.search(r"([0-9]+\.?[0-9]*)", content)
                        score = float(number_match.group(1)) if number_match else 0.5
                else:
                    score = 0.5

                reranked_docs.append({"document": doc, "score": score})
            except Exception as e:
                reranked_docs.append({"document": doc, "score": 0.5})

        reranked_docs.sort(key=lambda x: x["score"], reverse=True)

        return [item["document"] for item in reranked_docs]

    except Exception as e:
        print(f"Warning: Reranking failed, using original order: {e}")
        return documents


def _safe_text_from_response(response: Any) -> str:
    """Safely extract text from LLM response."""
    if hasattr(response, "content"):
        return response.content
    if isinstance(response, list) and response:
        first = response[0]
        return getattr(first, "content", str(first))
    return str(response)


@tool
def query_rag_policies(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """
    Query the bank's legal policies and regulations using RAG.

    Args:
        query: The search query for relevant policies
        top_k: Number of top results to return

    Returns:
        List of relevant policy excerpts with metadata
    """
    return _query_rag_store(query, top_k)


@tool
def extract_complaint_details(
    user_prompt: str, customer_context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Extract complaint details from the user prompt.

    Returns:
        Dict with customer_id, customer_name, complaint, main_problem, and assigned_tasks.
    """
    context_json = json.dumps(customer_context or {}, indent=2, default=str)

    system = """You are the Complaint Agent for a bank AI system.
Your job:
1. Parse the incoming user prompt and extract customer_id, customer_name, and complaint text.
2. Identify the core banking problem.
3. Decide which specialist agents need to be involved: reception, credit, commercial, signature_checks, fraud_detection, analysis_reporting, recovery.
4. For each selected agent, write a clear task description.

Use the customer context below when available:
{}

Respond ONLY with a valid JSON object:
{{
  "customer_id": "<client123>",
  "customer_name": "<Full Name>",
  "complaint": "<full complaint text>",
  "main_problem": "<one-sentence summary>",
  "assigned_tasks": [
    {{"agent": "<agent_name>", "task": "<what this agent should do>"}}
  ]
}}
No markdown, pure JSON.
""".format(context_json)

    human = f"User prompt:\n{user_prompt}"

    response = LLM.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    raw = response.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
        return parsed
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse complaint details: {str(e)}",
            "raw_response": raw,
        }


@tool
def fetch_customer_context(customer_id: str) -> dict[str, Any]:
    """
    Fetch customer context from MongoDB including accounts, transactions, etc.

    Args:
        customer_id: The customer ID (e.g., 'client123').

    Returns:
        Dict with collections of customer data.
    """
    # Accept either ObjectId format (24 hex chars) or clientXXX format
    object_id_pattern = r"[0-9a-fA-F]{24}"
    client_pattern = r"client\d+"

    if not (
        re.fullmatch(object_id_pattern, customer_id)
        or re.fullmatch(client_pattern, customer_id)
    ):
        return {
            "error": f"customer_id must be a valid ObjectId (24 hex chars) or 'client' + digits, got {customer_id}"
        }

    collections = [
        "customers",
        "bank_params",
        "bank_transactions",
        "cheques",
        "reclamations",
        "recovery_loans",
    ]

    context: dict[str, Any] = {}

    # First check if customer exists in customers collection
    # Use different filter based on ID format
    if re.fullmatch(r"[0-9a-fA-F]{24}", customer_id):
        # ObjectId format - search by _id
        customers_result = mcp_handle(
            {
                "action": "fetch",
                "collection": "customers",
                "filter": {"_id": customer_id},
            }
        )
    else:
        # clientXXX format - search by customer_id field
        customers_result = mcp_handle(
            {
                "action": "fetch",
                "collection": "customers",
                "filter": {"customer_id": customer_id},
            }
        )

    if customers_result["status"] == "success" and customers_result["data"]:
        # Customer exists, fetch all their data
        context["customers"] = customers_result["data"]

        # Fetch other collections
        for collection in [
            "accounts",
            "bank_params",
            "bank_transactions",
            "cheques",
            "reclamations",
            "recovery_loans",
        ]:
            filter_ = (
                {} if collection == "bank_params" else {"customer_id": customer_id}
            )
            result = mcp_handle(
                {
                    "action": "fetch",
                    "collection": collection,
                    "filter": filter_,
                }
            )
            if result["status"] == "success":
                context[collection] = result["data"]
            else:
                context[collection] = {"error": result.get("message")}
    else:
        # Customer does not exist - return clear error
        return {
            "error": f"Customer with ID '{customer_id}' not found in customers database. Please verify the customer ID or create the customer profile first.",
            "customers": [],
            "accounts": [],
            "reclamations": [],
            "bank_transactions": [],
            "cheques": [],
            "recovery_loans": [],
            "bank_params": [],
        }

    return context


@tool
def synthesize_agent_results(
    main_problem: str, agent_results_json: str
) -> dict[str, Any]:
    """
    Synthesize results from multiple agents.

    Args:
        main_problem: The core problem statement.
        agent_results_json: JSON string with agent results.

    Returns:
        Dict with resume (summary) and solved status.
    """
    system = """You are the Resume Agent for a bank AI system.
You receive outputs from multiple specialist agents and must:
1. Write a clear, concise summary for the client.
2. Decide if the complaint is fully resolved (true) or needs follow-up (false).

Respond ONLY with valid JSON:
{
  "resume": "<client-friendly summary>",
  "solved": true | false
}
Pure JSON, no markdown.
"""

    human = f"Main problem: {main_problem}\n\nAgent results:\n{agent_results_json}"

    response = LLM.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    raw = response.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
        if not parsed.get("solved"):
            parsed["resume"] = (
                f"{parsed['resume']} "
                "Please confirm one preferred appointment slot when validation times are proposed."
            )
        return parsed
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to synthesize results: {str(e)}",
            "resume": "Unable to process agent results.",
            "solved": False,
        }


@tool
def record_complaint(complaint_data: dict[str, Any]) -> dict[str, Any]:
    """
    Record a reclamation in the database.

    Args:
        complaint_data: Dict with customer_id, customer_name, complaint, main_problem, tasks.

    Returns:
        Dict with status and reclamation_id.
    """
    record = {
        "customer_id": complaint_data.get("customer_id"),
        "objet": complaint_data.get("main_problem"),
        "date": datetime.utcnow(),
        "date_rep": datetime.utcnow(),
        "status": False,
        "followed_up": False,
    }

    try:
        insert_result = mcp_handle(
            {
                "action": "insert",
                "collection": "reclamations",
                "data": record,
            }
        )

        if insert_result["status"] == "success":
            reclamation_id = insert_result["data"]["_id"]
            return {
                "status": "success",
                "reclamation_id": reclamation_id,
                "message": f"Reclamation recorded with ID {reclamation_id}",
            }
        else:
            return {
                "status": "error",
                "message": insert_result.get("message", "Unknown error"),
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to record reclamation: {str(e)}",
        }


@tool
def update_complaint(
    reclamation_id: str,
    update_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Update reclamation record in the database.

    Args:
        reclamation_id: The reclamation ID.
        update_data: Fields to update.

    Returns:
        Status of the update operation.
    """
    try:
        result = mcp_handle(
            {
                "action": "update",
                "collection": "reclamations",
                "filter": {"_id": reclamation_id},
                "data": update_data,
            }
        )
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update reclamation: {str(e)}",
        }


@tool
def suggest_booking_slots(user_id: str = None) -> list[dict[str, Any]]:
    """
    Suggest available booking slots based on bank hours and customer calendar.

    Args:
        user_id: User ID to check calendar availability

    Returns:
        List of suggested slots with start_time and end_time (ISO format strings).
    """
    try:
        suggested_slots = _suggest_booking_slots_local(user_id)
        formatted = [
            {
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "display": f"{start.strftime('%A %Y-%m-%d %H:%M')} - {end.strftime('%H:%M')}",
            }
            for start, end in suggested_slots
        ]
        return formatted
    except Exception as e:
        return [{"error": f"Failed to suggest slots: {str(e)}"}]


@tool
def book_appointment(
    start_time: str,
    end_time: str,
    summary: str = "Bank visit appointment",
    description: str = "",
    location: str = "",
) -> dict[str, Any]:
    """
    Book an appointment in Google Calendar.

    Args:
        start_time: ISO format datetime string (e.g., '2024-01-15T10:00:00')
        end_time: ISO format datetime string (e.g., '2024-01-15T11:00:00')
        summary: Event title
        description: Event description
        location: Event location

    Returns:
        Dict with booking status and details
    """
    event_data = {
        "start": start_time,
        "end": end_time,
        "summary": summary,
        "description": description,
        "location": location,
    }

    result = mcp_handle(
        {
            "action": "insert",
            "collection": "booking",
            "data": event_data,
        }
    )

    if result["status"] == "success":
        return {
            "status": "success",
            "message": "Appointment booked successfully",
            "event_id": result["data"]["_id"],
        }
    else:
        return {
            "status": "error",
            "message": result.get("message", "Failed to book appointment"),
        }


@tool
def generate_client_message(
    customer_name: str,
    complaint_summary: str,
    resolved: bool,
    follow_up_note: str = "",
) -> str:
    """
    Generate a client-facing message for the complaint resolution.

    Args:
        customer_name: Customers full name.
        complaint_summary: Summary of the complaint resolution.
        resolved: Whether the complaint is resolved.
        follow_up_note: Additional follow-up information if not resolved.

    Returns:
        Formatted client message.
    """
    if resolved:
        return f"Dear {customer_name},\n\nYour complaint has been resolved.\n\n{complaint_summary}\n\nThank you for reaching out to us."
    else:
        return f"Dear {customer_name},\n\nWe have reviewed your complaint and are still working on it.\n\n{complaint_summary}\n\nNext steps: {follow_up_note}\n\nWe will contact you shortly."


@tool
def query_rag_policies(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """
    Query the bank's legal policies and regulations using RAG.

    Args:
        query: The search query for relevant policies
        top_k: Number of top results to return

    Returns:
        List of relevant policy excerpts with metadata
    """
    return _query_rag_store(query, top_k)


@tool
def book_appointment(
    start_time: str,
    end_time: str,
    summary: str = "Bank visit appointment",
    description: str = "",
    location: str = "",
) -> dict[str, Any]:
    """
    Book an appointment in Google Calendar.

    Args:
        start_time: ISO format datetime string (e.g., '2024-01-15T10:00:00')
        end_time: ISO format datetime string (e.g., '2024-01-15T11:00:00')
        summary: Event title
        description: Event description
        location: Event location

        Returns:
        Dict with booking status and details
    """
    event_data = {
        "start": start_time,
        "end": end_time,
        "summary": summary,
        "description": description,
        "location": location,
    }

    result = mcp_handle(
        {
            "action": "insert",
            "collection": "bookings",
            "data": event_data,
        }
    )

    if result["status"] == "success":
        return {
            "status": "success",
            "message": "Appointment booked successfully",
            "event_id": result["data"]["_id"],
        }
    else:
        return {
            "status": "error",
            "message": result.get("message", "Failed to book appointment"),
        }


@tool
def generate_client_message(
    customer_name: str,
    complaint_summary: str,
    resolved: bool,
    follow_up_note: str = "",
) -> str:
    """
    Generate a client-facing message for the complaint resolution.

    Args:
        customer_name: Customers full name.
        complaint_summary: Summary of the complaint resolution.
        resolved: Whether the complaint is resolved.
        follow_up_note: Additional follow-up information if not resolved.

    Returns:
        Formatted client message.
    """
    if resolved:
        return f"Dear {customer_name},\n\nYour complaint has been resolved.\n\n{complaint_summary}\n\nThank you for reaching out to us."
    else:
        return f"Dear {customer_name},\n\nWe have reviewed your complaint and are still working on it.\n\n{complaint_summary}\n\nNext steps: {follow_up_note}\n\nWe will contact you shortly."


@tool
def book_followup(
    customer_id: str, booking_date: str, booking_subject: str, booking_time: str = None
) -> dict[str, Any]:
    """
    Book a follow-up appointment for a customer.

    Args:
        customer_id: The customer's ID (e.g., '69c2f3c6502ace17550a9a97').
        booking_date: The booking date (YYYY-MM-DD format).
        booking_subject: The subject/reason for the booking.
        booking_time: The booking time (HH:MM format, optional).

    Returns:
        Dict with booking status and booking_id.
    """
    from datetime import datetime
    from db.mcp_handler import app_client, APP_MONGO_DB_NAME

    try:
        # Validate date format
        datetime.strptime(booking_date, "%Y-%m-%d")

        # Validate customer ID format (ObjectId or clientXXX)
        object_id_pattern = r"[0-9a-fA-F]{24}"
        client_pattern = r"client\d+"

        if not (
            re.fullmatch(object_id_pattern, customer_id)
            or re.fullmatch(client_pattern, customer_id)
        ):
            return {
                "status": "error",
                "message": f"customer_id must be a valid ObjectId (24 hex chars) or 'client' + digits, got {customer_id}",
            }

        booking_record = {
            "customer_id": customer_id,
            "booking_date": booking_date,
            "booking_time": booking_time,
            "booking_subject": booking_subject,
            "status": "scheduled",
            "created_at": datetime.utcnow(),
        }

        booking_collection = app_client[APP_MONGO_DB_NAME]["booking"]
        booking_record["created_at"] = datetime.utcnow()

        try:
            booking_id = booking_collection.insert_one(booking_record)
            return {
                "status": "success",
                "booking_id": str(booking_id.inserted_id),
                "message": f"Follow-up booking confirmed for {customer_id} on {booking_date}{' at ' + booking_time if booking_time else ''}",
                "booking_details": {
                    "customer_id": customer_id,
                    "date": booking_date,
                    "time": booking_time,
                    "subject": booking_subject,
                    "booking_id": str(booking_id.inserted_id),
                },
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to book follow-up: {str(e)}",
            }

    except ValueError:
        return {
            "status": "error",
            "message": "Invalid date format. Please use YYYY-MM-DD format.",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to book follow-up: {str(e)}",
        }


@tool
def check_booking_availability(user_id: str, date: str) -> dict[str, Any]:
    """
    Check if user has availability on a specific date.

    Args:
        user_id: User ID to check calendar
        date: Date to check (YYYY-MM-DD format)

    Returns:
        Dict with availability status and existing events.
    """
    from datetime import datetime
    from db.mcp_handler import google_auth_db

    try:
        # Parse date
        check_date = datetime.strptime(date, "%Y-%m-%d")

        # Get user calendar events
        users_collection = google_auth_db["users"]
        user_doc = users_collection.find_one({"google_id": user_id})

        if not user_doc:
            return {
                "status": "error",
                "message": f"User {user_id} not found in system",
                "available": False,
            }

        # Get events for the specific date
        user_events = user_doc.get("calendar_events", [])
        date_events = []

        for event in user_events:
            if "start_time" in event and "end_time" in event:
                event_start = datetime.fromisoformat(event["start_time"])
                if event_start.date() == check_date.date():
                    date_events.append(event)

        return {
            "status": "success",
            "date": date,
            "events": date_events,
            "available": len(date_events) == 0,
            "message": f"You have {len(date_events)} events on {date}"
            if date_events
            else f"You are free on {date}",
        }

    except ValueError:
        return {
            "status": "error",
            "message": "Invalid date format. Please use YYYY-MM-DD format.",
            "available": False,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to check availability: {str(e)}",
            "available": False,
        }


# Get all tools
AVAILABLE_TOOLS = [
    extract_complaint_details,
    fetch_customer_context,
    synthesize_agent_results,
    record_complaint,
    update_complaint,
    suggest_booking_slots,
    generate_client_message,
    query_rag_policies,
    book_appointment,
    book_followup,
    check_booking_availability,
]
