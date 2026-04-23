import json
from typing import Dict, Any
from ..pi_utils.db_mongo import mcp_handle
from ..pi_utils.db_neo4j import neo4j_handler
from datetime import datetime

# LangChain imports
from .tools import get_user_profile, query_neo4j_graph
from .agent_factory import create_structured_agent_executor, EXECUTION_SYSTEM_PROMPT

# Lazy initialization
_execution_executor = None

def get_execution_executor():
    """Lazy initialization of the execution agent executor."""
    global _execution_executor
    if _execution_executor is None:
        tools = [get_user_profile, query_neo4j_graph]
        _execution_executor = create_structured_agent_executor(
            tools=tools,
            system_prompt=EXECUTION_SYSTEM_PROMPT,
            max_iterations=3,
            verbose=False
        )
    return _execution_executor


def execution_agent(state):
    """
    Simulates budget update and portfolio change.
    Persists data in MongoDB + Neo4j.
    """
    user_id = state.get("user_id", "default_user")
    profile = state.get("profile", {})
    persona = state.get("persona", "neutral")
    recommendations = state.get("recommendations", [])
    
    # Update MongoDB profile via MCP
    mcp_handle({
        "action": "update",
        "collection": "users",
        "filter": {"user_id": user_id},
        "data": {"profile": profile, "persona": persona}
    })
    
    # Save recommendations to MongoDB via MCP
    mcp_handle({
        "action": "insert",
        "collection": "recommendations",
        "data": {
            "user_id": user_id,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat()
        }
    })
    
    # Update Neo4j relationships
    neo4j_handler.create_persona_relationship(user_id, persona)
    for rec in recommendations:
        if rec.get("decision") == "BUY":
            neo4j_handler.create_interest_relationship(user_id, profile.get("goal"), rec.get("asset"))
        
    state["executed"] = True
    return state
