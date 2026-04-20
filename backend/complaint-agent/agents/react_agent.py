from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from pymongo import MongoClient

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import BaseTool
from dotenv import load_dotenv

from agents.tools import AVAILABLE_TOOLS
from db.mcp_handler import mcp_handle, GOOGLE_AUTH_MONGO_URI, GOOGLE_AUTH_MONGO_DB_NAME

# Load environment
dotenv_path = Path(__file__).resolve().parents[1] / ".env"
if not dotenv_path.exists():
    dotenv_path = Path(__file__).resolve().parents[2] / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()

LLM = ChatOpenAI(
    model=os.getenv("FASTFIN_LLM_MODEL", "qwen/qwen3-vl-4b"),
    base_url=os.getenv("FASTFIN_LLM_BASE_URL", "http://localhost:1234/v1"),
    api_key=os.getenv("FASTFIN_LLM_API_KEY", "lm-studio"),
    temperature=0.7,
)

# Bind tools to LLM
LLM_WITH_TOOLS = LLM.bind_tools(AVAILABLE_TOOLS)

REACT_SYSTEM_PROMPT = """You are an intelligent Bank Complaint Resolution Agent.

You follow the ReAct (Reasoning + Acting) pattern:
1. **Think**: Analyze the complaint and what information is needed
2. **Act**: Use available tools to gather data and take actions
3. **Observe**: Check results and decide next steps
4. **Clarify**: Ask the user for missing critical information

Available Tools:
- extract_complaint_details: Parse complaint and identify tasks
- fetch_customer_context: Get customer data from database (note: empty arrays mean no data, not errors!)
- call_subagent: Delegate to specialized agents (reception, credit, commercial, signature_checks, fraud_detection, analysis_reporting, recovery)
- synthesize_agent_results: Combine results from multiple agents
- record_complaint: Save reclamation to database
- update_complaint: Update reclamation record
- suggest_booking_slots: Get available appointment times (checks user calendar)
- check_booking_availability: Check if user is free on specific date
- generate_client_message: Create professional response
- query_rag_policies: Search bank policies and regulations
- book_appointment: Schedule a meeting in Google Calendar
- book_followup: Book follow-up appointment in booking collection

Instructions:
1. **Check memory first**: Look for stored user information like customer_id before asking
2. **Use memory**: Remember user information like customer_id, name, etc. for future interactions
3. **Customer ID is already provided**: The customer's ID is stored in memory, use it directly
4. **Empty results are OK**: If fetch returns empty arrays (reclamations=[], bookings=[]), it means the customer has no complaints/bookings - this is normal, not an error!
5. **Fetch customer context**: Use the customer_id from memory to fetch their data
6. **Query policies**: Use RAG to find relevant bank policies when user has a complaint/problem
7. **Process systematically**:
   - Extract → Fetch context → Query policies (if needed) → Record → Execute subagents → Synthesize → Generate response → Update
8. **Be conversational**: If information is missing, ask politely rather than failing silently
9. **Explain your reasoning**: Show the user what you're doing and thinking
10. **Book appointments**: When suggesting slots, also offer to book them if user agrees
11. **Adapt**: If a tool fails, try alternative approaches

IMPORTANT: The customer_id "69b92442f777189171928caa" is valid. If you get empty arrays in results, it just means no data exists yet - that's fine!

If you need information from the user, ask clearly and wait for their response."""


class ReactAgent:
    """Dynamic ReAct agent for complaint processing."""

    def __init__(
        self,
        max_iterations: int = 10,
        verbose: bool = True,
        user_id: str | None = None,
        google_access_token: str | None = None,
    ):
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.user_id = user_id
        self.google_access_token = google_access_token
        self.conversation_history: list[dict[str, Any]] = []
        self.tool_results: dict[str, Any] = {}
        self.memory: dict[str, Any] = {}  # In-memory storage only

    def _load_memory(self):
        """Load user memory from MongoDB if user_id is provided."""
        pass  # Using in-memory storage only

    def _save_memory(self):
        """Save user memory to MongoDB if user_id is provided."""
        pass  # Using in-memory storage only

    def remember_user_info(self, key: str, value: Any):
        """Store user information in memory."""
        self.memory[key] = value

    def store_conversation_resumee(self, resumee: str):
        """Store the resumee of the conversation in memory."""
        self.memory["last_resumee"] = resumee

    def get_user_info(self, key: str) -> Any:
        """Retrieve user information from memory."""
        return self.memory.get(key)

    def get_conversation_resumee(self) -> str:
        """Get the last conversation resumee."""
        return self.memory.get("last_resumee", "")

    def _print_step(self, label: str, content: str):
        """Print a reasoning step if verbose mode is enabled."""
        if self.verbose:
            print(f"\n[{label}]\n{content}")

    def _execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute a tool and return the result as a string."""
        for tool in AVAILABLE_TOOLS:
            if tool.name == tool_name:
                try:
                    # Add google_access_token from memory if needed for booking tools
                    if tool_name in [
                        "book_appointment",
                        "suggest_booking_slots",
                        "check_booking_availability",
                    ]:
                        google_token = self.get_user_info("google_access_token")
                        if google_token:
                            tool_input["google_access_token"] = google_token

                    result = tool.func(**tool_input)
                    # Store user info in memory if available
                    if tool_name == "extract_complaint_details" and isinstance(
                        result, dict
                    ):
                        if "customer_id" in result:
                            self.remember_user_info(
                                "customer_id", result["customer_id"]
                            )
                        if "customer_name" in result:
                            self.remember_user_info(
                                "customer_name", result["customer_name"]
                            )

                    # Store conversation resumee in memory when synthesis is complete
                    if tool_name == "synthesize_agent_results" and isinstance(
                        result, dict
                    ):
                        if "resume" in result:
                            self.store_conversation_resumee(result["resume"])
                            if self.verbose:
                                print(
                                    f"Stored conversation resumee in memory: {result['resume'][:100]}..."
                                )

                    return json.dumps(result, default=str)
                except Exception as e:
                    return json.dumps({"error": str(e), "tool": tool_name})
        return json.dumps({"error": f"Tool '{tool_name}' not found"})

    def run(self, user_input: str) -> dict[str, Any]:
        """
        Run the ReAct agent loop with the given user input.

        Args:
            user_input: The customer's complaint or question

        Returns:
            Final result with complaint resolution
        """
        # Don't reset conversation_history if we have previous context
        if not self.conversation_history:
            self.conversation_history = []
            self.tool_results = {}

        iteration = 0

        self._print_step("START", f"Processing: {user_input}")

        # Add current user message to history
        self.conversation_history.append(
            {
                "role": "user",
                "content": user_input,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Save conversation to memory
        self._save_memory()

        while iteration < self.max_iterations:
            iteration += 1
            self._print_step("ITERATION", str(iteration))

            # Get agent response
            messages = [
                {"role": "system", "content": REACT_SYSTEM_PROMPT},
            ]

            # Add memory context if available
            if self.memory:
                memory_str = f"User Memory: {json.dumps(self.memory, indent=2)}"
                messages.append({"role": "system", "content": memory_str})

            messages.extend(self.conversation_history)

            # Convert to LangChain message format
            lc_messages = [
                HumanMessage(content=msg["content"])
                if msg["role"] == "user"
                else AIMessage(content=msg["content"])
                for msg in messages[1:]
            ]

            # Get response from LLM
            response = LLM_WITH_TOOLS.invoke(lc_messages)

            response_content = response.content or ""
            self._print_step("REASONING", response_content)

            # Check for tool calls
            if hasattr(response, "tool_calls") and response.tool_calls:
                # Add AI message to history
                self.conversation_history.append(
                    {
                        "role": "assistant",
                        "content": response_content,
                    }
                )

                # Execute tools
                all_tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name") or tool_call.get("type")
                    tool_input = tool_call.get("args", {})

                    self._print_step(
                        "TOOL CALL", f"{tool_name}({json.dumps(tool_input)})"
                    )

                    result = self._execute_tool(tool_name, tool_input)
                    self.tool_results[tool_name] = json.loads(result)

                    all_tool_results.append(
                        {
                            "tool": tool_name,
                            "input": tool_input,
                            "output": result,
                        }
                    )

                    self._print_step(
                        "TOOL RESULT",
                        result[:200] + "..." if len(result) > 200 else result,
                    )

                # Add tool results to conversation
                self.conversation_history.append(
                    {
                        "role": "user",
                        "content": f"Tool results:\n{json.dumps(all_tool_results, indent=2, default=str)}",
                    }
                )

            else:
                # No tool calls means agent is done or asking a question
                self.conversation_history.append(
                    {
                        "role": "assistant",
                        "content": response_content,
                    }
                )

                # Check if agent is asking for information
                if any(
                    word in response_content.lower()
                    for word in [
                        "what is",
                        "please provide",
                        "could you",
                        "customer id",
                        "need",
                        "require",
                    ]
                ):
                    # Agent is asking a clarifying question
                    self._print_step(
                        "AWAITING INPUT", "Agent is asking for information from user"
                    )

                    # Save conversation state to memory
                    self._save_memory()

                    return {
                        "status": "awaiting_input",
                        "message": response_content,
                        "conversation_history": self.conversation_history,
                        "tool_results": self.tool_results,
                    }

                # Agent completed the task
                self._print_step("COMPLETE", response_content)

                # Save final conversation state to memory
                self._save_memory()

                return {
                    "status": "complete",
                    "message": response_content,
                    "conversation_history": self.conversation_history,
                    "tool_results": self.tool_results,
                }

        return {
            "status": "max_iterations",
            "message": "Reached maximum iterations",
            "conversation_history": self.conversation_history,
            "tool_results": self.tool_results,
        }

    def continue_conversation(self, user_input: str) -> dict[str, Any]:
        """
        Continue an ongoing ReAct conversation.

        Args:
            user_input: User's response to clarifying question or next input

        Returns:
            Updated result
        """
        # Add user response to history
        self.conversation_history.append(
            {
                "role": "user",
                "content": user_input,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Save conversation to memory
        self._save_memory()

        # Continue the agent loop from where it left off
        return self.run_from_history()

    def run_from_history(self) -> dict[str, Any]:
        """Continue running agent from current conversation history."""
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1

            # Get agent response
            messages = [
                {"role": "system", "content": REACT_SYSTEM_PROMPT},
            ]

            # Add memory context if available
            if self.memory:
                memory_str = f"User Memory: {json.dumps(self.memory, indent=2)}"
                messages.append({"role": "system", "content": memory_str})

            messages.extend(self.conversation_history)

            # Convert to LangChain message format
            lc_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    lc_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    lc_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    lc_messages.append(AIMessage(content=msg["content"]))

            # Get response from LLM
            response = LLM_WITH_TOOLS.invoke(lc_messages)

            response_content = response.content or ""
            self._print_step("REASONING", response_content)

            # Check for tool calls
            if hasattr(response, "tool_calls") and response.tool_calls:
                # Add AI message
                self.conversation_history.append(
                    {
                        "role": "assistant",
                        "content": response_content,
                    }
                )

                # Execute tools
                all_tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name") or tool_call.get("type")
                    tool_input = tool_call.get("args", {})

                    self._print_step(
                        "TOOL CALL", f"{tool_name}({json.dumps(tool_input)})"
                    )

                    result = self._execute_tool(tool_name, tool_input)
                    self.tool_results[tool_name] = json.loads(result)

                    all_tool_results.append(
                        {
                            "tool": tool_name,
                            "input": tool_input,
                            "output": result,
                        }
                    )

                    self._print_step(
                        "TOOL RESULT",
                        result[:200] + "..." if len(result) > 200 else result,
                    )

                # Add results to conversation
                self.conversation_history.append(
                    {
                        "role": "user",
                        "content": f"Tool results:\n{json.dumps(all_tool_results, indent=2, default=str)}",
                    }
                )

            else:
                # No tool calls
                self.conversation_history.append(
                    {
                        "role": "assistant",
                        "content": response_content,
                    }
                )

                # Check if asking for more info
                if any(
                    word in response_content.lower()
                    for word in [
                        "what is",
                        "please provide",
                        "could you",
                        "customer id",
                        "need",
                    ]
                ):
                    self._print_step(
                        "AWAITING INPUT", "Agent is asking for information"
                    )
                    return {
                        "status": "awaiting_input",
                        "message": response_content,
                        "conversation_history": self.conversation_history,
                        "tool_results": self.tool_results,
                    }

                # Task complete
                self._print_step("COMPLETE", response_content)
                return {
                    "status": "complete",
                    "message": response_content,
                    "conversation_history": self.conversation_history,
                    "tool_results": self.tool_results,
                }

        return {
            "status": "max_iterations",
            "message": "Reached maximum iterations",
            "conversation_history": self.conversation_history,
            "tool_results": self.tool_results,
        }


def run_react_agent(
    user_input: str,
    verbose: bool = True,
    user_id: str | None = None,
    customer_id: str | None = None,
    google_access_token: str | None = None,
) -> dict[str, Any]:
    """
    Run the ReAct agent with the given input.

    Args:
        user_input: The customer's complaint
        verbose: Whether to print reasoning steps
        user_id: User identifier for memory persistence
        customer_id: Pre-set customer ID for the user
        google_access_token: Google OAuth token for calendar access

    Returns:
        Result dict with status, message, and conversation history
    """
    if not hasattr(run_react_agent, "_agent_instances"):
        run_react_agent._agent_instances = {}

    if user_id and user_id in run_react_agent._agent_instances:
        agent = run_react_agent._agent_instances[user_id]
    else:
        agent = ReactAgent(
            verbose=verbose, user_id=user_id, google_access_token=google_access_token
        )
        if user_id:
            run_react_agent._agent_instances[user_id] = agent

    if customer_id:
        agent.remember_user_info("customer_id", customer_id)

    if google_access_token:
        agent.remember_user_info("google_access_token", google_access_token)

    return agent.run(user_input)
