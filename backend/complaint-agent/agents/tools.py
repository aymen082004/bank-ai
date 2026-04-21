
from __future__ import annotations

import json
import os
import re
import sys
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from db.mcp_handler import mcp_handle
from dotenv import load_dotenv
from functools import lru_cache


dotenv_path = Path(__file__).resolve().parents[2] / ".env"
if not dotenv_path.exists():
    dotenv_path = Path(__file__).resolve().parents[1] / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dot_env()


def _fetch_google_calendar_events(google_access_token: str, time_min: datetime, time_max: datetime) -> list[dict]:
    """
    Fetch live events from user's Google Calendar.
    
    Note: Requires valid OAuth token with refresh capability. If token is invalid,
    returns empty list and falls back to local slot suggestion.

    The google_access_token can be either:
    - Access token (for immediate use, expires in 1 hour)
    - Refresh token (starts with ya29., used to get new access token)

    Args:
        google_access_token: Google OAuth access token or refresh token
        time_min: Start of time range to fetch events
        time_max: End of time range to fetch events

    Returns:
        List of event dicts with 'start' and 'end' keys
    """
    if not google_access_token:
        return []
    
    from db.mcp_handler import _init_google_calendar_service
    
    is_refresh_token = google_access_token.startswith("ya29.")
    
    service = _init_google_calendar_service(
        google_access_token=None if is_refresh_token else google_access_token,
        google_refresh_token=google_access_token if is_refresh_token else None,
    )
    if not service:
        return []

    try:
        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min.isoformat() + "Z",
            timeMax=time_max.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for event in events_result.get("items", []):
            start = event.get("start", {})
            end = event.get("end", {})

            start_time = start.get("dateTime") or start.get("date")
            end_time = end.get("dateTime") or end.get("date")

            if start_time and end_time:
                events.append({
                    "start_time": start_time,
                    "end_time": end_time,
                })

        return events
    except Exception as e:
        print(f"Warning: Failed to fetch Google Calendar events: {e}")
        return []


def _suggest_booking_slots_local(google_access_token: str = None) -> list[tuple]:

    from datetime import datetime, timedelta, timedelta, time

    now = datetime.now()
    slots = []

    user_calendar_events = []

    if google_access_token:
        try:
            time_min = now
            time_max = now + timedelta(days=14)
            user_calendar_events = _fetch_google_calendar_events(
                google_access_token, time_min, time_max
            )
        except Exception as e:
            print(f"Warning: Could not fetch Google Calendar: {e}")

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

    return slots[:3]


def _query_rag_store(query: str, top_k: int = 1) -> list[dict[str, Any]]:
    """Query the bank's legal policies and regulations using RAG."""
    import os
    os.environ["CHROMA_TELEMETRY_DISABLED"] = "true"
    
    import chromadb
    from langchain_ollama import OllamaEmbeddings


    try:
        legal_dir = Path(__file__).parent / "ressources" / "chromadb"
        
        client = chromadb.PersistentClient(path=str(legal_dir))
        
        try:
            collection = client.get_collection("loi_2016_48")
        except Exception:
            collection = client.create_collection("loi_2016_48")
        
        count = collection.count()
        print(f"[RAG] Documents: {count}")

        if count == 0:
            return [{"error": "RAG collection is empty"}]

        embeddings = OllamaEmbeddings(model="mxbai-embed-large:latest")
        query_embedding = embeddings.embed_query(query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        if not results or not results.get("documents") or not results["documents"][0]:
            return [{"error": "No results found"}]

        docs = []
        for i, doc_text in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            docs.append({
                "text": doc_text[:500],
                "metadata": metadata,
            })
        return docs

    except Exception as e:
        print(f"RAG Error: {e}")
        import traceback
        traceback.print_exc()
        return [{"error": str(e)}]


def _safe_text_from_response(response: Any) -> str:
    """Safely extract text from LLM response."""
    if hasattr(response, "content"):
        return response.content
    if isinstance(response, list) and response:
        first = response[0]
        return getattr(first, "content", str(first))
    return str(response)


@tool
def query_rag_policies(query: str) -> list[dict[str, Any]]:
    """
    Query the bank's legal policies and procedures from RAG.
    
    IMPORTANT: Use this BEFORE taking any action to resolve a customer problem!
    This searches the bank's knowledge base containing:
    - Legal regulations (loi_2016_48, banking compliance)
    - Internal procedures (NP-131010.pdf documents)
    - Customer service workflows
    
    When to use:
    - When a customer describes a problem or issue
    - When you need to know the correct procedure/policy to resolve something
    - Before offering a solution or giving advice
    - ANY time you don't know the correct procedure
    
    What to query:
    - For account issues: "compte bloque debloquer procedure"
    - For card issues: "carte bloquee replacement procedure"
    - For fees: "frais bancaire contestation procedure"
    - For transfers: "virement international procedure"
    - For refunds: "remboursement client procedure"
    
    Args:
        query: Natural language search query in French describing the problem/situation
               Use French keywords: "carte bloquee", "compte bloque", "frais", "cheque", "virement"

    Returns:
        List of relevant policy excerpts with:
        - text: The policy/procedure content (truncated to 500 chars)
        - metadata: source document name
    """
    return _query_rag_store(query, 1)


@tool
def fetch_customer_context(
    customer_id: str,
    table: str,
) -> dict[str, Any]:
    """
Retrieve structured customer data from MongoDB for a SINGLE table.

This tool is the primary source of truth for customer-related investigation.

Core principles:
- Fetch ONLY one table per call (strict rule)
- Use progressively based on the problem context
- Interpret results, do NOT just display raw data

Smart usage strategy:
1. Start with "customers" → identity validation
2. Then:
   - "accounts" → balance / blocked issues
   - "bank_transactions" → payment disputes
   - "recovery_loans" → loan-related complaints
   - "bookings" → appointment issues
   - etc.

Validation:
- customer_id must be valid MongoDB ObjectId (24 hex chars)
- Automatically attempts fallback (_id vs customer_id)

Edge cases:
- Empty result ≠ error → means no data exists
- Missing customer → returns explicit error

Args:
    customer_id: MongoDB ObjectId (required)
    table: Target collection name (one only)

Returns:
    {
        "<table_name>": [data] OR [],
        "error": optional error message
    }

Agent behavior expectations:
- ALWAYS interpret results
- ALWAYS connect data to complaint
- NEVER say "no data" without explanation
"""
    import re
    from bson.objectid import ObjectId


    valid_tables = [
        "customers",
        "accounts",
        "bank_transactions",
        "cheques",
        "reclamations",
        "recovery_loans",
        "bookings",
        "bank_cards",
    ]

    if not table:
        return {
            "error": f"Please specify which table to fetch. Valid options: {', '.join(valid_tables)}."
        }

    table = table.lower()
    if table not in valid_tables:
        return {
            "error": f"Invalid table '{table}'. Valid options: {', '.join(valid_tables)}."
        }

    object_id_pattern = r"[0-9a-fA-F]{24}"

    if not customer_id:
        return {
            "error": "customer_id is required (MongoDB ObjectId format: 24 hex characters).",
            table: [],
        }

    if not re.fullmatch(object_id_pattern, customer_id):
        return {
            "error": f"customer_id must be a valid ObjectId (24 hex chars), got {customer_id}"
        }

    context: dict[str, Any] = {}

    customers_result = mcp_handle(
        {
            "action": "fetch",
            "collection": "customers",
            "filter": {"customer_id": ObjectId(customer_id)},
        }
    )

    if customers_result["status"] != "success" or not customers_result["data"]:
        customers_result = mcp_handle(
            {
                "action": "fetch",
                "collection": "customers",
                "filter": {"_id": ObjectId(customer_id)},
            }
        )

    if customers_result["status"] != "success" or not customers_result["data"]:
        return {
            "error": f"Customer with ID '{customer_id}' not found in customers collection.",
            table: [],
        }

    customer_data = customers_result["data"]
    actual_customer_id = customer_id
    if customer_data:
        actual_customer_id = customer_data[0].get("customer_id") or customer_data[0].get("_id")

    if table == "customers":
        context[table] = customer_data
        return context

    filter_ = {"customer_id": actual_customer_id}
    result = mcp_handle(
        {
            "action": "fetch",
            "collection": table,
            "filter": filter_,
        }
    )

    if result["status"] == "success":
        context[table] = result["data"]
    else:
        context[table] = {"error": result.get("message")}

    return context


@tool
def record_complaint(complaint_data: dict[str, Any]) -> dict[str, Any]:
    """
Persist a finalized complaint into the system.

CRITICAL: This is a TERMINAL action.

Only call this when:
- The issue is fully resolved, OR
- A follow-up appointment has been confirmed

Mandatory confirmation before calling:
- "Votre problème est-il résolu ?" → YES
OR
- "Ce rendez-vous est-il confirmé ?" → YES

Behavior:
- Stores complaint metadata in MongoDB
- Converts dates to ISO format
- Tracks resolution or follow-up status

Status meanings:
- en_attente → unresolved
- traite → handled (often with booking)
- resolu → fully resolved

Args:
    complaint_data: Structured complaint object

Returns:
    {
        "status": "success" | "error",
        "reclamation_id": str,
        "message": str
    }

Agent warning:
- NEVER call this prematurely
- NEVER assume resolution without explicit user confirmation
"""
    from datetime import datetime, timedelta

    record = {
        "customer_id": complaint_data.get("customer_id"),
        "objet": complaint_data.get("objet"),
        "date": datetime.strptime(complaint_data.get("date"), "%Y-%m-%d").isoformat(),
        "date_rep": datetime.strptime(complaint_data.get("date_rep"), "%Y-%m-%d").isoformat(),
        "status": complaint_data.get("status"),
        "followed_up": bool(complaint_data.get("followed_up")),
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
    Update an existing complaint/reclamation. Use when:
    - User reports problem still persists after initial resolution
    - User wants to change booking date
    - Status needs to be updated

    Fields for update_data:
    - `objet`: Updated subject (optional)
    - `description`: Updated description (optional)
    - `date_rep`: New booking date or resolution date (optional, YYYY-MM-DD)
    - `status`: New status (optional)
        - "en_attente": Back to pending
        - "en_cours": Being processed
        - "traite": Resolved with booking
        - "resolu": Fully resolved

    Args:
        reclamation_id: The reclamation ID to update (24 hex chars).
        update_data: Dict with fields to update.

    Returns:
        Dict with status and message.
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
def suggest_booking_slots(
    google_access_token: str = None,
) -> list[dict[str, Any]]:
    """
Generate user-facing appointment suggestions.

This is the ENTRY POINT for any scheduling workflow.

Workflow enforcement:
1. Call this tool
2. Present options clearly to the user
3. Ask confirmation
4. ONLY THEN call booking tool

Enhancements over local logic:
- Formats slots into human-readable form
- Includes structured fields for UI or LLM reasoning

Returns:
    [
        {
            "slot_date": "YYYY-MM-DD",
            "slot_time": "HH:MM",
            "start_time": ISO,
            "end_time": ISO,
            "display": readable string
        }
    ]

Agent rules:
- NEVER skip this step before booking
- ALWAYS ask: "Ce créneau est-il confirmé ?"
"""
    try:
        suggested_slots = _suggest_booking_slots_local(google_access_token)
        formatted = [
            {
                "slot_date": start.strftime("%Y-%m-%d"),
                "slot_time": start.strftime("%H:%M"),
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
    customer_id: str,
    date: str,
    time: str,
    google_access_token: str = None,
    appointment_type: str = "Rendez-vous bancaire",
    description: str = "",
) -> dict[str, Any]:
    """
Create a confirmed bank appointment and optionally sync with Google Calendar.

STRICT RULE: Only call AFTER user confirmation.

Responsibilities:
- Store booking in MongoDB
- Optionally create Google Calendar event
- Ensure consistent scheduling record

Flow:
- Input must match a previously suggested slot
- Automatically sets status = "confirmed"

Failure handling:
- If DB insert fails → abort
- If calendar fails → continue (non-blocking)

Args:
    customer_id: Required
    date: YYYY-MM-DD
    time: HH:MM
    google_access_token: Optional
    appointment_type: Context label
    description: Optional details

Returns:
    Booking confirmation with IDs

Agent behavior:
- NEVER invent a slot
- NEVER call without confirmation
"""
    from datetime import datetime, timedelta

    booking_data = {
        "customer_id": customer_id,
        "date": date,
        "time": time,
        "type": appointment_type,
        "description": description,
        "status": "confirmed",
    }

    mongo_result = mcp_handle(
        {
            "action": "insert",
            "collection": "bookings",
            "data": booking_data,
        }
    )

    booking_id = None
    calendar_event_id = None

    if mongo_result["status"] == "success":
        booking_id = mongo_result["data"]["_id"]
    else:
        return {
            "status": "error",
            "message": mongo_result.get("message", "Failed to book appointment"),
        }

    if google_access_token:
        try:
            from db.mcp_handler import _create_google_calendar_event

            start_dt = datetime.fromisoformat(f"{date}T{time}:00")
            end_dt = start_dt + timedelta(hours=1)

            calendar_event = _create_google_calendar_event(
                google_access_token=google_access_token,
                summary=appointment_type,
                description=description or f"Booking ID: {booking_id}",
                start_time=start_dt.isoformat(),
                end_time=end_dt.isoformat(),
            )

            if calendar_event:
                calendar_event_id = calendar_event.get("id")
        except Exception as e:
            print(f"Warning: Failed to create calendar event: {e}")

    return {
        "status": "success",
        "message": f"Appointment scheduled for {date} at {time}",
        "booking_id": booking_id,
        "calendar_event_id": calendar_event_id,
    }

@tool
def book_followup(
    customer_id: str,
    slot_date: str,
    slot_time: str,
    google_access_token: str = None,
    appointment_type: str = "Rendez-vous bancaire",
    description: str = "",
) -> dict[str, Any]:
    """
    Book a follow-up appointment. Use ONLY with slots from suggest_booking_slots.

    IMPORTANT: Only call this AFTER user confirms the slot.

    Workflow:
    1. Call suggest_booking_slots() first
    2. Present options to user
    3. Get user confirmation for specific slot
    4. Call book_followup() with the confirmed slot

    Args:
        customer_id: Customer ID (24 hex chars) - REQUIRED
        slot_date: Date from suggested slots (YYYY-MM-DD) - REQUIRED
        slot_time: Time from suggested slots (HH:MM) - REQUIRED
        google_access_token: Google OAuth token (optional)
        appointment_type: Type of appointment (default: "Rendez-vous bancaire")
        description: Additional notes (optional)

    Returns:
        Dict with booking status, booking_id, and calendar_event_id.
    """
    from datetime import datetime, timedelta

    if not customer_id or not slot_date or not slot_time:
        return {
            "status": "error",
            "message": "customer_id, slot_date, and slot_time are all required.",
        }

    booking_data = {
        "customer_id": customer_id,
        "date": slot_date,
        "time": slot_time,
        "type": appointment_type,
        "description": description,
        "status": "confirmed",
    }

    mongo_result = mcp_handle(
        {
            "action": "insert",
            "collection": "bookings",
            "data": booking_data,
        }
    )

    booking_id = None
    calendar_event_id = None

    if mongo_result["status"] == "success":
        booking_id = mongo_result["data"]["_id"]
    else:
        return {
            "status": "error",
            "message": mongo_result.get("message", "Failed to book follow-up"),
        }

    if google_access_token:
        try:
            from db.mcp_handler import _create_google_calendar_event

            start_dt = datetime.fromisoformat(f"{slot_date}T{slot_time}:00")
            end_dt = start_dt + timedelta(hours=1)

            calendar_event = _create_google_calendar_event(
                google_access_token=google_access_token,
                summary=appointment_type,
                description=description or f"Booking ID: {booking_id}",
                start_time=start_dt.isoformat(),
                end_time=end_dt.isoformat(),
            )

            if calendar_event:
                calendar_event_id = calendar_event.get("id")
        except Exception as e:
            print(f"Warning: Failed to create calendar event: {e}")

    return {
        "status": "success",
        "message": f"Follow-up booked for {slot_date} at {slot_time}",
        "booking_id": booking_id,
        "calendar_event_id": calendar_event_id,
    }


@tool
def redirect_to_agent(complaint_type: str) -> str:
    """
Initiate redirection to a specialized agent (credit or reception).

Use ONLY when:
- The request clearly falls خارج your scope
- Example:
   - Loan applications → credit agent
   - Account opening → reception agent

Mandatory step:
Ask user confirmation BEFORE calling this tool.

Args:
    complaint_type: "credit" or "reception"

Returns:
    A confirmation message asking user approval

Agent behavior:
- Do not force redirect
- Present as guided assistance, not rejection
"""
    if complaint_type == "credit":
        return """Je vais vous rediriger vers le service Crédit.
        
Pour confirmer, devez-vous être redirigé vers l'agent Crédit pour votre demande de prêt ou crédit?"""
    elif complaint_type == "reception":
        return """Je vais vous rediriger vers le service Accueil.
        
Pour confirmer, devez-vous être redirigé vers l'agent Accueil pour l'ouverture de compte?"""
    else:
        return """Type de redirection non reconnu. Veuillez spécifier 'credit' ou 'reception'."""


def get_redirect_info(complaint_text: str) -> str | None:
    """
    Analyze complaint to determine if it needs redirection to another agent.
    
    Returns the redirect type if detected, None otherwise.
    """
    text_lower = complaint_text.lower()
    
    credit_keywords = ["pret", "credit", "emprunt", "financement", "loan", "crédit"]
    reception_keywords = ["compte", "ouvrir", "accueillir", "accueil", "nouveau client", "opening"]
    
    for kw in credit_keywords:
        if kw in text_lower:
            return "credit"
    for kw in reception_keywords:
        if kw in text_lower:
            return "reception"
    return None


# Get all tools
AVAILABLE_TOOLS = [
    query_rag_policies,
    fetch_customer_context,
    record_complaint,
    update_complaint,
    suggest_booking_slots,
    book_appointment,
    book_followup,
    redirect_to_agent,
]
