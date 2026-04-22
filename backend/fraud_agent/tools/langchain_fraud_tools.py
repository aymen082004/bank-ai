# tools/langchain_fraud_tools.py
"""
LangChain Tool wrappers for fraud detection.
These tools are called autonomously by the LangChain ReAct agent.
"""

import pandas as pd
from typing import Optional
from langchain.tools import tool

from fraud_agent.db.mongo import account_collection, card_collection
from services.prediction_service import predict_account_service, predict_card_service


# ==========================================
# 🔧 SHARED RISK SCORE CALCULATOR
# ==========================================
def _compute_risk(df_result: pd.DataFrame) -> dict:
    """Internal helper – computes standardised risk metrics from a scored DataFrame."""
    scores = pd.to_numeric(df_result.get("final_score", pd.Series(dtype=float)), errors="coerce").fillna(0)
    avg_score       = float(scores.mean())
    max_score       = float(scores.max())
    high_risk_ratio = float((scores > 0.8).mean())
    # Same normalised formula as ScoreRiskEngine in enhanced_fraud_agent.py
    normalized      = avg_score * 0.3 + max_score * 0.4 + high_risk_ratio * 0.3
    risk_score      = normalized * 10
    return {
        "avg_score":       round(avg_score, 4),
        "max_score":       round(max_score, 4),
        "high_risk_ratio": round(high_risk_ratio, 4),
        "risk_score":      round(risk_score, 4),
    }


# ==========================================
# 🔧 TOOL 1 – ACCOUNT ANALYSIS
# ==========================================
def analyze_account_transactions(
    client_id: str,
    label: Optional[str] = None,
    date: Optional[str] = None,
    year: Optional[int] = None,
) -> dict:
    """
    Fetch and score account (virement / bank-transfer) transactions for a client.

    Use this tool FIRST to evaluate account-level fraud risk.

    Args:
        client_id: Client identifier, e.g. 'client181'.
        label: Optional label filter – 'Suspicious', 'Fraud', or 'Non-Fraud'.
        date: Optional specific date in YYYY-MM-DD format.
        year: Optional year to filter (YYYY).

    Returns:
        dict with keys:
          - status         : 'success' | 'no_data' | 'error'
          - total_tx       : number of transactions analysed
          - avg_score      : average anomaly score (0-1)
          - max_score      : maximum anomaly score (0-1)
          - high_risk_ratio: fraction of transactions scoring > 0.8
          - risk_score     : composite risk score (0-10, higher = riskier)
    """
    try:
        query = {"client": {"$regex": f"^{client_id.strip()}\\s*$"}}
        if label:
            query["label"] = label
        if date:
            query["date"] = {"$regex": f"^{date}"}
        elif year:
            query["date"] = {"$regex": f"^{year}"}

        data = list(account_collection.find(query))
        if not data:
            return {
                "status":   "no_data",
                "message":  f"No account transactions found for {client_id}",
                "total_tx": 0,
                "risk_score": 0.0,
            }

        df        = pd.DataFrame(data)
        df_result = predict_account_service(df)

        # Optional post-filters (year / date)
        if "datetime" in df_result.columns:
            df_result["datetime"] = pd.to_datetime(df_result["datetime"], errors="coerce")
            if year:
                df_result = df_result[df_result["datetime"].dt.year == int(year)]
            if date:
                df_result = df_result[df_result["datetime"].dt.date == pd.to_datetime(date).date()]
        if label and "final_label" in df_result.columns:
            df_result = df_result[df_result["final_label"] == label]

        metrics = _compute_risk(df_result)
        return {
            "status":    "success",
            "client_id": client_id,
            "total_tx":  len(df_result),
            **metrics,
        }

    except Exception as e:
        return {"status": "error", "message": f"Account analysis failed: {str(e)}", "risk_score": 0.0}


# ==========================================
# 🔧 TOOL 2 – CARD ANALYSIS
# ==========================================
def analyze_card_transactions(
    client_id: str,
    label: Optional[str] = None,
    date: Optional[str] = None,
    carte_id: Optional[str] = None,
) -> dict:
    """
    Fetch and score card (payment / POS) transactions for a client.

    Use this tool AFTER account analysis to check card-level risk.
    If the client has no card data, the tool returns status='no_data' – that is fine.

    Args:
        client_id: Client identifier, e.g. 'client181'.
        label: Optional label filter – 'Suspicious', 'Fraud', or 'Non-Fraud'.
        date: Optional specific date in YYYY-MM-DD format.
        carte_id: Optional specific card identifier.

    Returns:
        dict with keys:
          - status         : 'success' | 'no_data' | 'error'
          - total_tx       : number of transactions analysed
          - avg_score      : average anomaly score (0-1)
          - max_score      : maximum anomaly score (0-1)
          - high_risk_ratio: fraction of transactions scoring > 0.8
          - risk_score     : composite risk score (0-10, higher = riskier)
    """
    try:
        query = {"client": {"$regex": f"^{client_id.strip()}\\s*$"}}
        if carte_id:
            query["carte"] = {"$regex": f"^{carte_id.strip()}\\s*$"}
        if label:
            query["label"] = label
        if date:
            query["date"] = {"$regex": f"^{date}"}

        data = list(card_collection.find(query))
        if not data:
            return {
                "status":   "no_data",
                "message":  f"No card transactions found for {client_id}",
                "total_tx": 0,
                "risk_score": 0.0,
            }

        df = pd.DataFrame(data)
        for col in ["client", "compte", "carte"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        df_result = predict_card_service(df)

        if "datetime" in df_result.columns:
            df_result["datetime"] = pd.to_datetime(df_result["datetime"], errors="coerce")
            if date:
                df_result = df_result[df_result["datetime"].dt.date == pd.to_datetime(date).date()]
        if label and "final_label" in df_result.columns:
            df_result = df_result[df_result["final_label"] == label]

        metrics = _compute_risk(df_result)
        return {
            "status":    "success",
            "client_id": client_id,
            "total_tx":  len(df_result),
            **metrics,
        }

    except Exception as e:
        return {"status": "error", "message": f"Card analysis failed: {str(e)}", "risk_score": 0.0}


# ==========================================
# 🔧 TOOL 3 – GRAPH RAG INSIGHT
# ==========================================
def get_graph_insight(client_id: str) -> dict:
    """
    Retrieve graph-based behavioural intelligence for a client from the Neo4j knowledge graph.

    Use this tool to enrich the analysis with network-level signals (shared accounts,
    suspicious connections, community patterns).

    Args:
        client_id: Client identifier, e.g. 'client181'.

    Returns:
        dict with keys:
          - status         : 'success' | 'error'
          - connections    : list of connected entities
          - llm_explanation: narrative description of graph behaviour
          - raw_insights   : raw graph signals
    """
    try:
        from ..graph.graph_rag import graph_rag_insight
        result = graph_rag_insight(client_id)
        return {
            "status":          "success",
            "client_id":       client_id,
            "connections":     result.get("connections", []),
            "llm_explanation": result.get("llm_explanation", "No graph explanation available."),
            "raw_insights":    result.get("raw_insights", []),
            "features":        result.get("features", {}),
            "subgraph":        result.get("subgraph", {}),
            "viz_html":        result.get("viz_html", ""),
        }
    except Exception as e:
        return {
            "status":          "error",
            "message":         f"Graph insight failed: {str(e)}",
            "connections":     [],
            "llm_explanation": "Graph unavailable.",
        }


# ==========================================
# 🔧 TOOL 4 – ML EXPLAINABILITY
# ==========================================
def get_ml_explainability(
    client_id: str,
    account_risk_score: float,
    card_risk_score: float = 0.0,
) -> dict:
    """
    Generate detailed ML feature-importance explainability for the fraud analysis.

    Use this tool after you have risk scores from account and card analysis to get
    a human-readable explanation of which features drove the anomaly scores.

    Args:
        client_id: Client identifier, e.g. 'client181'.
        account_risk_score: Risk score from analyze_account_transactions (0-10).
        card_risk_score: Risk score from analyze_card_transactions (0-10), default 0.

    Returns:
        dict with a 'llm_context' string suitable for inclusion in the final explanation.
    """
    try:
        from ..services.explainability import create_detailed_explanation
        from ..db.mongo import account_collection, card_collection
        from ..services.prediction_service import predict_account_service, predict_card_service

        # Minimal re-fetch for explainability
        acc_query = {"client": {"$regex": f"^{client_id.strip()}\\s*$"}}
        acc_data  = list(account_collection.find(acc_query))
        acc_df    = predict_account_service(pd.DataFrame(acc_data)) if acc_data else pd.DataFrame()

        card_data = list(card_collection.find(acc_query))
        card_df   = None
        if card_data:
            raw = pd.DataFrame(card_data)
            for col in ["client", "compte", "carte"]:
                if col in raw.columns:
                    raw[col] = raw[col].astype(str).str.strip()
            card_df = predict_card_service(raw)

        result = create_detailed_explanation(
            client_id=client_id,
            account_data=acc_df,
            card_data=card_df,
            account_scores={
                "ae_score":   float(acc_df["ae_score"].mean())   if not acc_df.empty and "ae_score"   in acc_df.columns else 0.0,
                "lstm_score": float(acc_df["lstm_score"].mean()) if not acc_df.empty and "lstm_score" in acc_df.columns else 0.0,
                "risk_score": account_risk_score,
            },
            card_scores={
                "ae_score":   float(card_df["ae_score"].mean())   if card_df is not None and "ae_score"   in card_df.columns else 0.0,
                "lstm_score": float(card_df["lstm_score"].mean()) if card_df is not None and "lstm_score" in card_df.columns else 0.0,
                "risk_score": card_risk_score,
            } if card_df is not None else None,
        )
        return {
            "status":      "success",
            "llm_context": result.get("llm_context", "No ML explainability context available."),
        }
    except Exception as e:
        return {
            "status":      "error",
            "message":     f"Explainability failed: {str(e)}",
            "llm_context": "",
        }


# ==========================================
# 🔧 TOOL 5 – FRAUD DECISION
# ==========================================
def make_fraud_decision(
    account_risk_score: float,
    card_risk_score: float = 0.0,
) -> dict:
    """
    Make the final fraud detection decision based on composite risk scores.

    ALWAYS call this tool last, after you have collected account and card risk scores.

    Args:
        account_risk_score: Risk score from account analysis (0-10).
        card_risk_score: Risk score from card analysis (0-10), default 0 if no card data.

    Returns:
        dict with keys:
          - decision    : 'Fraud' | 'Suspicious' | 'Non-Fraud'
          - confidence  : float 0-1
          - total_score : combined risk score
          - reason      : short human-readable reason
    """
    total_score = account_risk_score + card_risk_score

    # Hard rule: card anomaly alone can trigger Fraud
    if card_risk_score >= 8:
        return {
            "decision":    "Fraud",
            "confidence":  0.95,
            "total_score": round(total_score, 4),
            "reason":      "Card anomaly detected – immediate block recommended",
        }

    if total_score >= 12:
        decision, confidence, reason = "Fraud",      0.95, "High combined risk across account and card"
    elif total_score >= 6:
        decision, confidence, reason = "Suspicious", 0.75, "Moderate anomalies detected – monitor closely"
    else:
        decision, confidence, reason = "Non-Fraud",  0.90, "Normal behaviour – no action needed"

    return {
        "decision":    decision,
        "confidence":  confidence,
        "total_score": round(total_score, 4),
        "reason":      reason,
    }


# ==========================================
# 📦 EXPORT
# ==========================================
def get_fraud_detection_tools():
    """Returns ordered list of LangChain tools for the fraud detection agent.

    Wraps the callable functions with `langchain.tools.tool` so the returned
    objects are usable by LangChain agents while keeping the original
    functions callable programmatically.
    """
    try:
        return [
            tool(analyze_account_transactions),
            tool(analyze_card_transactions),
            tool(get_graph_insight),
            tool(get_ml_explainability),
            tool(make_fraud_decision),
        ]
    except Exception:
        # If langchain.tools.tool is not available for some reason, fall back
        # to returning the raw callables so programmatic calls still work.
        return [
            analyze_account_transactions,
            analyze_card_transactions,
            get_graph_insight,
            get_ml_explainability,
            make_fraud_decision,
        ]
