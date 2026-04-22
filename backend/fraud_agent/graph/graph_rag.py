from graph.graph_queries import GraphAnalyzer
from services.graph_llm_explainer import generate_graph_llm_explanation
import os
import logging
import services.logger
from graph.visualizer import render_visjs_html

logger = logging.getLogger(__name__)

# Read Neo4j credentials from environment with fallback to existing values
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://70ee550a.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "70ee550a")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "GByyMxE1-oqZpmZXyJBRtoWSQonSshxnX-I2aL7vFig")

graph = GraphAnalyzer(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)


# ==========================================
# GRAPH SIGNAL EXTRACTION (NO SCORING)
# ==========================================
def graph_rag_insight(client_id):

    # Fetch raw values from graph; coerce None -> sensible defaults
    linked = graph.find_linked_clients(client_id) or []

    try:
        shared_users = graph.shared_merchants(client_id)
        shared_users = int(shared_users) if shared_users is not None else 0
    except Exception as e:
        logger.exception("Error fetching shared_merchants for %s: %s", client_id, e)
        shared_users = 0

    try:
        peak_tx = graph.transaction_peak(client_id)
        peak_tx = int(peak_tx) if peak_tx is not None else 0
    except Exception as e:
        logger.exception("Error fetching transaction_peak for %s: %s", client_id, e)
        peak_tx = 0

    try:
        cards = graph.count_cards(client_id)
        cards = int(cards) if cards is not None else 0
    except Exception as e:
        logger.exception("Error fetching count_cards for %s: %s", client_id, e)
        cards = 0

    try:
        merchants = graph.count_merchants(client_id)
        merchants = int(merchants) if merchants is not None else 0
    except Exception as e:
        logger.exception("Error fetching count_merchants for %s: %s", client_id, e)
        merchants = 0

    # -------------------------
    # STEP 1: BUILD RAW INSIGHTS (RULE-BASED SIGNALS ONLY)
    # -------------------------
    insights = []

    if shared_users > 0:
        insights.append(f"{shared_users} shared merchant connections detected")

    if shared_users > 3:
        insights.append(f"High network overlap: {shared_users} shared users across merchants")

    if peak_tx > 10:
        insights.append(f"Transaction spike detected: {peak_tx} peak transactions in a day")

    if peak_tx > 50:
        insights.append(f"Extreme burst activity: {peak_tx} transactions in single day")

    if merchants > 10:
        insights.append(f"High merchant diversity: {merchants} merchants interacted")

    if cards > 1:
        insights.append(f"Multiple cards detected: {cards} cards linked to client")

    # fallback
    if not insights:
        insights.append("No abnormal graph behavior detected")

    # -------------------------
    # STEP 2: LLM INTERPRETATION
    # -------------------------
    llm_summary = graph_rag_llm_summary(insights)

    # -------------------------
    # OUTPUT
    # -------------------------
    # Try to build a subgraph for visualization (best-effort)
    try:
        subgraph = graph.get_client_subgraph(client_id) or {"nodes": [], "edges": []}
        viz_html = render_visjs_html(subgraph)
    except Exception as e:
        logger.exception("Failed to build visualization for %s: %s", client_id, e)
        subgraph = {"nodes": [], "edges": []}
        viz_html = ""

    return {
        "connections": linked,
        "features": {
            "cards": cards,
            "merchants": merchants,
            "peak_tx": peak_tx,
            "shared_users": shared_users
        },
        "raw_insights": insights,
        "llm_explanation": llm_summary,
        "subgraph": subgraph,
        "viz_html": viz_html,
    }


# ==========================================
# GRAPH → LLM EXPLANATION MODULE
# ==========================================
def graph_rag_llm_summary(insights):
    """
    Converts graph signals → human behavioral explanation (NO SCORING)
    """

    prompt = f"""
Vous êtes un analyste en investigation de fraude.

Convertissez ces signaux en insights comportementaux.

RÈGLES ABSOLUES :
- N'assignez PAS de probabilité ou décision
- Pas de markdown (**, ##, -, *, etc.)
- Texte simple, 2-3 phrases maximum
- Décrivez UNIQUEMENT les patterns comportementaux suspects
- Pas de répétition de "Décision" ou "Signaux"

Signaux :
{chr(10).join(insights)}
"""

    return generate_graph_llm_explanation(prompt)