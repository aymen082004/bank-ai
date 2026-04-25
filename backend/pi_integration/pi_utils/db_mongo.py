import os
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

# Connexion MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://alexhunter2020111_db_user:HUrHSfVkpCL1CrAb@cluster0.0rav9u6.mongodb.net/?appName=Cluster0")
DB_NAME = os.getenv("DB_NAME", "bank_ai")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def get_collection(name):
    return db[name]

# --- MCP Handler ---
def mcp_handle(message: dict) -> dict:
    """
    message = {
        "action": "fetch" / "update" / "insert",
        "collection": "customers",
        "filter": {...},
        "data": {...}
    }
    """
    response = {"status": "error", "data": None}

    try:
        action = message.get("action")
        collection_name = message.get("collection")
        collection = db[collection_name]

        if action == "fetch":
            results = list(collection.find(message.get("filter", {})))
            # Convert ObjectId en str
            for r in results:
                r["_id"] = str(r["_id"])
            response = {"status": "success", "data": results}

        elif action == "update":
            filter_query = message.get("filter", {})
            update_data = {"$set": message.get("data", {})}
            result = collection.update_many(filter_query, update_data)
            response = {"status": "success", "data": {"matched": result.matched_count, "modified": result.modified_count}}

        elif action == "insert":
            data = message.get("data", {})
            # If data contains non-serializable objects, convert them if necessary
            # For now keeping it simple as per user's provided code
            collection.insert_one(data)
            # MongoDB adds _id to dict after insert
            if "_id" in data:
                data["_id"] = str(data["_id"])
            response = {"status": "success", "data": {"_id": data.get("_id")}}

        else:
            response = {"status": "error", "message": "Action inconnue"}

        # Log audit
        print(f"[{datetime.utcnow()}] MCP {action} on {collection_name}: {message.get('filter', message.get('data', {}))}")

    except Exception as e:
        response = {"status": "error", "message": str(e)}

    return response

# Compatibility helpers for existing code
def get_user_transactions(user_id):
    res = mcp_handle({
        "action": "fetch",
        "collection": "transactions",
        "filter": {"user_id": user_id}
    })
    return res.get("data", []) if res.get("status") == "success" else []

def save_transaction(user_id, amount, category, description):
    return mcp_handle({
        "action": "insert",
        "collection": "transactions",
        "data": {
            "user_id": user_id,
            "amount": amount,
            "category": category,
            "description": description,
            "timestamp": datetime.utcnow().isoformat()
        }
    })
