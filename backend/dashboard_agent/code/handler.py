"""
Handler MongoDB — LECTURE SEULE.
fetch, count, aggregate uniquement.
"""
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
import os

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://alexhunter2020111_db_user:HUrHSfVkpCL1CrAb@cluster0.0rav9u6.mongodb.net/?appName=Cluster0"
)

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _client.admin.command("ping")
        print("[DB] MongoDB Atlas connecté — lecture seule")
    return _client["bank_ai"]


def _clean(doc):
    if isinstance(doc, list):
        return [_clean(i) for i in doc]
    if not isinstance(doc, dict):
        return doc
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _clean(v)
        elif isinstance(v, list):
            out[k] = [_clean(i) for i in v]
        else:
            out[k] = v
    return out


def fetch(collection: str, filtre: dict = {}, projection: dict = None,
          sort: dict = None, limit: int = 50) -> list:
    db  = get_db()
    cur = db[collection].find(filtre, projection)
    if sort:
        k, v = list(sort.items())[0]
        cur  = cur.sort(k, v)
    return _clean(list(cur.limit(limit)))


def count(collection: str, filtre: dict = {}) -> int:
    return get_db()[collection].count_documents(filtre)


def aggregate(collection: str, pipeline: list) -> list:
    return _clean(list(get_db()[collection].aggregate(pipeline)))
