"""
🎯 Fraud Agent – Natural Language Entry Point
============================================
Accepts any free-text query → runs the real LangChain ReAct agent → returns analysis.

Examples:
    "Check fraud for client181"
    "Analyze client962 suspicious transactions"
    "Verify client181 card fraud on 2021-01-04"
    "Check fraud for client100 in 2021"
"""
from .langchain_fraud_agent import langchain_fraud_agent
import logging
from services import logger as services_logger

logger = logging.getLogger(__name__)


def fraud_agent_text(text: str) -> dict:
    """
    Simple interface: Accept text → LangChain ReAct agent → structured result.

    The underlying agent autonomously:
      1. Extracts the client ID from the query
      2. Calls account & card analysis tools
      3. Optionally fetches graph RAG insights & ML explainability
      4. Makes the final fraud decision
      5. Returns a human-readable explanation

    Args:
        text (str): Natural language query about a client's fraud analysis.

    Returns:
        dict: Complete analysis with decision, scores, and explanation.
    """
    if not text or not text.strip():
        return {
            "error": "Please provide a text query, e.g., 'Check fraud for client181'"
        }

    return langchain_fraud_agent(text)


# ===========================
# EXAMPLE USAGE
# ===========================
if __name__ == "__main__":
    test_queries = [
        "Check fraud for client181",
        "Analyze client962 suspicious only",
        "verify client181 fraud transactions on 2021-01-04",
        "Check fraud for client100 in 2021",
    ]

    for query in test_queries:
        logger.info("Query: %s", query)
        logger.info("%s", "-" * 60)
        result = fraud_agent_text(query)
        if "error" in result:
            logger.error("%s", result['error'])
        else:
            logger.info("Decision: %s", result.get('decision'))
            logger.info("Risk Score: %s", result.get('total_risk_score'))
            logger.info("Confidence: %s", result.get('confidence'))
            logger.info("Explanation: %s", result.get('final_explanation', 'N/A'))
