from .mongo import results_collection, account_collection, card_collection
from datetime import datetime
import logging
import services.logger

logger = logging.getLogger(__name__)

def save_fraud_result(result: dict):
    """
    Save the fraud analysis result into MongoDB.
    Separates account, card, and overall results.
    """
    try:
        client_id = result.get("client_id")
        timestamp = result.get("timestamp", datetime.now().isoformat())

        # Save account transactions
        account_data = result.get("account", {})
        if account_data:
            account_collection.insert_one({
                "client_id": client_id,
                "timestamp": timestamp,
                **account_data
            })

        # Save card transactions if any
        card_data = result.get("card")
        if card_data:
            card_collection.insert_one({
                "client_id": client_id,
                "timestamp": timestamp,
                **card_data
            })

        # Save final fraud result
        results_collection.insert_one({
            "client_id": client_id,
            "timestamp": timestamp,
            "decision": result.get("decision"),
            "confidence": result.get("confidence"),
            "total_risk_score": result.get("total_risk_score"),
            "explanation": result.get("explanation", {}),
            "label_filter": result.get("label_filter", None)
        })

        return True
    except Exception as e:
        logger.exception("MongoDB save error: %s", e)
        return False