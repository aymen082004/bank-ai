import os
import sys
from datetime import datetime
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://alexhunter2020111_db_user:HUrHSfVkpCL1CrAb@cluster0.0rav9u6.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["bank_ai"]

print("--- Inspecting 'reclamations' date_rep types ---")
rep_types = db["reclamations"].aggregate([
    {"$group": {"_id": {"$type": "$date_rep"}, "count": {"$sum": 1}}}
])
print(f"Reclamations date_rep types: {list(rep_types)}")
