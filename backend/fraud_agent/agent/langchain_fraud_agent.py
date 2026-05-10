# agent/langchain_fraud_agent.py
import sys, io
# Fix Windows console encoding so emoji/unicode in prints don't crash the process
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
"""
Real LangChain ReAct Agent for Fraud Detection
===============================================
Replaces the hardcoded pipeline in enhanced_fraud_agent.py with a genuine
agentic loop: the LLM autonomously decides which tools to call, inspects
their outputs, and reasons step-by-step to a final fraud decision.

Entry point:  langchain_fraud_agent(text: str) -> dict
"""

import re
import json
import traceback
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from tools.langchain_fraud_tools import get_fraud_detection_tools
from fraud_agent.db.db_utils import save_fraud_result
import logging
from services import logger as services_logger

logger = logging.getLogger(__name__)



# ==========================================
# ⚙️  LLM  (OpenRouter)
# ==========================================
llm = ChatOpenAI(
    model=os.getenv("OPENROUTER_MODEL", "mistralai/ministral-14b-2512"),
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
    temperature=0,
    max_tokens=1500,
)

# ==========================================
# 🛠️  TOOLS
# ==========================================
tools = get_fraud_detection_tools()

# ==========================================
# 🤖  AGENT  (LangGraph ReAct)
# ==========================================
SYSTEM_PROMPT = """Vous êtes un agent expert en détection de fraude pour une banque.
Vous avez accès à cinq outils :

1. analyze_account_transactions  – évalue les transactions de compte/virement (toujours appeler celui-ci en premier)
2. analyze_card_transactions     – évalue les transactions de carte/POS (appeler celui-ci en deuxième)
3. get_graph_insight             – récupère les signaux réseau/graph de Neo4j
4. get_ml_explainability         – produit le contexte d'importance des caractéristiques pour votre explication
5. make_fraud_decision           – calcule la décision finale (appeler celui-ci EN DERNIER)

Votre travail :
    a) Appelez analyze_account_transactions avec le client_id extrait de la requête utilisateur.
    b) Appelez analyze_card_transactions avec le même client_id.
    c) Appelez get_graph_insight et get_ml_explainability pour enrichir l'analyse (toujours les appeler).
    d) Appelez make_fraud_decision avec les valeurs de risk_score que vous avez obtenues.
    e) Rédigez une réponse finale avec :
             - La décision de fraude (Fraude / Suspect / Non-Fraude)
             - Le score de confiance
             - Une explication en langage simple (2-4 phrases) décrivant ce qui est anormal

Règles :
    - Extrayez le client_id de la requête utilisateur (format : clientNNN, ex. client181).
    - Appelez toujours get_graph_insight et get_ml_explainability pour chaque requête.
    - N'inventez PAS de données. Utilisez uniquement ce que les outils retournent.
    - Ne PAS sauter make_fraud_decision.
    - Pas de markdown (**, ##, -), pas de répétition de la décision.
    - Pas de jargon technique (Autoencoder, LSTM, modèle, algorithme).
    - Expliquez comme à un agent bancaire en langage simple.
"""

agent_executor = create_react_agent(llm, tools)


# ==========================================
# 🔍  HELPERS
# ==========================================
def _extract_client_id(text: str) -> Optional[str]:
    """Regex fallback to extract client_id from free text."""
    match = re.search(r"client[\s_-]?(\d+)", text, re.IGNORECASE)
    return f"client{match.group(1)}" if match else None


def _parse_tool_results(messages) -> Dict[str, Any]:
    """Walk agent message history and collect tool outputs."""
    account_result = {}
    card_result    = {}
    graph_result   = {}
    decision_result= {}
    explain_result = {}

    for msg in messages:
        if isinstance(msg, ToolMessage):
            try:
                content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
            except Exception:
                content = {}

            name = getattr(msg, "name", "") or ""
            if "account" in name:
                account_result = content
            elif "card" in name:
                card_result = content
            elif "graph" in name:
                graph_result = content
            elif "explainability" in name or "ml_expl" in name:
                explain_result = content
            elif "decision" in name:
                decision_result = content

    return {
        "account_result": account_result,
        "card_result":    card_result,
        "graph_result":   graph_result,
        "explain_result": explain_result,
        "decision_result":decision_result,
    }


def _build_final_result(
    client_id: str,
    tool_data: Dict[str, Any],
    agent_final_answer: str,
) -> Dict[str, Any]:
    """Assemble the standardised output dict (same shape as fraud_agent_v3)."""

    acc  = tool_data["account_result"]
    card = tool_data["card_result"]
    dec  = tool_data["decision_result"]
    grph = tool_data["graph_result"]
    expl = tool_data["explain_result"]

    has_card = bool(card) and card.get("status") == "success"

    # Fall back gracefully if make_fraud_decision was not called
    decision   = dec.get("decision",    "Unknown")
    confidence = dec.get("confidence",  0.0)
    total_score= dec.get("total_score", 0.0)
    reason     = dec.get("reason",      "")

    result = {
        "client_id":        client_id,
        "timestamp":        datetime.now().isoformat(),

        # Core decision
        "decision":         decision,
        "confidence":       confidence,
        "total_risk_score": total_score,
        "reason":           reason,

        # Per-channel summaries
        "account": {
            "total_tx":        acc.get("total_tx", 0),
            "avg_score":       acc.get("avg_score", 0.0),
            "max_score":       acc.get("max_score", 0.0),
            "high_risk_ratio": acc.get("high_risk_ratio", 0.0),
            "risk_score":      acc.get("risk_score", 0.0),
        },
        "card": {
            "total_tx":        card.get("total_tx", 0),
            "avg_score":       card.get("avg_score", 0.0),
            "max_score":       card.get("max_score", 0.0),
            "high_risk_ratio": card.get("high_risk_ratio", 0.0),
            "risk_score":      card.get("risk_score", 0.0),
        } if has_card else None,
        "has_card": has_card,

        # Explanations
        "ml_explainability":    expl,
        "graph_explanation":    grph.get("llm_explanation", ""),
        "graph":                grph,
        "final_explanation":    agent_final_answer,

        # Agent metadata
        "agent_type": "langchain_react",
    }

    return result


# ==========================================
# 🚀  MAIN ENTRY POINT
# ==========================================
def langchain_fraud_agent(text: str) -> Dict[str, Any]:
    """
    Real LangChain ReAct fraud detection agent.

    Accepts any natural language query such as:
      - "Check fraud for client181"
      - "Analyse client962 suspicious transactions"
      - "Verify client181 card fraud on 2021-01-04"

    Returns a dict with the same structure as the legacy fraud_agent_v3.
    """

    if not text or not text.strip():
        return {"error": "Please provide a query, e.g. 'Check fraud for client181'"}

    # Quick sanity-check: do we at least see a client id?
    client_id = _extract_client_id(text)
    if not client_id:
        return {
            "error": "Could not extract a client ID from your query.",
            "hint":  "Use a format like: 'Check fraud for client181'",
            "input": text,
        }

    logger.info("🤖 LangChain ReAct Agent starting for %s", client_id)
    logger.info("Query: %s", text)

    # ----------------------------------------
    # Build the messages for the agent
    # ----------------------------------------
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=text),
    ]

    try:
        # Invoke the agent – this runs the full ReAct loop
        response = agent_executor.invoke({"messages": messages})

        all_messages = response.get("messages", [])

        # Extract the final AI text answer
        final_answer = ""
        for msg in reversed(all_messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_answer = msg.content
                break

        # Collect all tool outputs from the message history
        tool_data = _parse_tool_results(all_messages)

        # Programmatic fallback: if the LLM did not call graph or explainability tools,
        # call them directly to ensure these analyses are always present.
        try:
            if not tool_data.get("graph_result"):
                logger.info("Agent did not produce graph results — invoking get_graph_insight() fallback.")
                from tools.langchain_fraud_tools import get_graph_insight
                tool_data["graph_result"] = get_graph_insight(client_id)
        except Exception as e:
            logger.exception("Fallback get_graph_insight error: %s", e)

        try:
            if not tool_data.get("explain_result"):
                logger.info("Agent did not produce ML explainability — invoking get_ml_explainability() fallback.")
                from tools.langchain_fraud_tools import get_ml_explainability
                acc_risk = 0
                if tool_data.get("account_result"):
                    acc_risk = tool_data["account_result"].get("risk_score", 0)
                card_risk = 0
                if tool_data.get("card_result"):
                    card_risk = tool_data["card_result"].get("risk_score", 0)
                tool_data["explain_result"] = get_ml_explainability(client_id, acc_risk, card_risk)
        except Exception as e:
            logger.exception("Fallback get_ml_explainability error: %s", e)

        # Build standardised result dict
        result = _build_final_result(client_id, tool_data, final_answer)

        logger.info("Decision: %s (confidence=%s)", result['decision'], result['confidence'])
        logger.info("Score: %s", result['total_risk_score'])

        # ── Ask an LLM judge to produce a bank-friendly final report ─────
        try:
            from services.enhanced_llm_service import generate_judge_report
            judge_report = generate_judge_report(result)
            result['bank_report'] = judge_report
        except Exception as e:
            logger.exception("Judge LLM error: %s", e)
            result['bank_report'] = {"error": str(e)}

        # Persist to MongoDB
        try:
            save_fraud_result(result)
        except Exception as e:
            logger.exception("MongoDB save error: %s", e)

        return result

    except Exception as e:
        logger.exception("Agent error: %s", e)
        return {
            "error":     f"Agent execution failed: {str(e)}",
            "client_id": client_id,
            "input":     text,
        }


# ==========================================
# 🧪  QUICK SMOKE TEST
# ==========================================
if __name__ == "__main__":
    test_queries = [
        "Check fraud for client181",
        "Analyse client962 suspicious transactions",
        "Verify client181 fraud on 2021-01-04",
    ]

    for query in test_queries:
        logger.info("%s", "=" * 65)
        logger.info("Query: %s", query)
        logger.info("%s", "=" * 65)
        result = langchain_fraud_agent(query)

        if "error" in result:
            logger.error("%s", result['error'])
        else:
            logger.info("Decision: %s", result.get('decision'))
            logger.info("Confidence: %s", result.get('confidence'))
            logger.info("Score: %s", result.get('total_risk_score'))
            logger.info("Explanation: %s", result.get('final_explanation', ''))
