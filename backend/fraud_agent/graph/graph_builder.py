# graph/graph_builder.py

from db.mongo import card_collection, account_collection
from graph.neo4j_loader import Neo4jLoader
from datetime import datetime
import logging
import services.logger

logger = logging.getLogger(__name__)

loader = Neo4jLoader(
    uri="neo4j+s://70ee550a.databases.neo4j.io",
    user="70ee550a",
    password="GByyMxE1-oqZpmZXyJBRtoWSQonSshxnX-I2aL7vFig"
)

def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return None
# -------------------------
# NORMALIZATION
# -------------------------
def normalize_card_tx(doc):
    return {
        "client": str(doc.get("client")).strip(),
        "account": str(doc.get("compte")).strip(),
        "card": str(doc.get("carte") or "NO_CARD").strip(),
        "merchant": (doc.get("nom_term commercant") or "UNKNOWN").strip().upper(),
        "amount": float(doc.get("mnt_autorise") or 0),
        "date": format_date(doc.get("dat_trans")),  # 🔥 FIX
        "source": "CARD"
    }


def normalize_account_tx(doc):
    return {
        "client": str(doc.get("client")).strip(),
        "account": str(doc.get("compte")).strip(),
        "card": "NO_CARD",  # 🔥 important
        "merchant": "ACCOUNT_OP",
        "amount": float(doc.get("montant_mvt") or 0),
        "date": format_date(doc.get("date_op")),  # 🔥 FIX
        "source": "ACCOUNT"
    }


# -------------------------
# MAIN LOADER
# -------------------------
def load_all_data(limit=10000, batch_size=500):

    loader.create_indexes()

    batch = []

    # -------------------------
    # LOAD CARD TRANSACTIONS
    # -------------------------
    logger.info("Loading card transactions...")

    for doc in card_collection.find().limit(limit):
        tx = normalize_card_tx(doc)

        if not tx["client"] or not tx["account"]:
            continue

        batch.append(tx)

        if len(batch) >= batch_size:
            loader.create_transactions_batch(batch)
            batch = []

    # -------------------------
    # LOAD ACCOUNT TRANSACTIONS
    # -------------------------
    logger.info("Loading account transactions...")

    for doc in account_collection.find().limit(limit):
        tx = normalize_account_tx(doc)

        if not tx["client"] or not tx["account"]:
            continue

        batch.append(tx)

        if len(batch) >= batch_size:
            loader.create_transactions_batch(batch)
            batch = []

    # remaining
    if batch:
        loader.create_transactions_batch(batch)

    logger.info("ALL DATA LOADED SUCCESSFULLY")