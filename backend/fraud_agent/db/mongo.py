from pymongo import MongoClient
import os
import logging
import services.logger

logger = logging.getLogger(__name__)

# Read Mongo URI from environment; fallback to previous value for now.
MONGO_URI = os.getenv(
	"MONGO_URI",
	"mongodb+srv://alexhunter2020111_db_user:HUrHSfVkpCL1CrAb@cluster0.0rav9u6.mongodb.net/?appName=Cluster0",
)
MONGO_DB = os.getenv("MONGO_DB", "bank_ai")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

try:
	# quick connectivity check
	client.admin.command("ping")
	logger.info("Connected to MongoDB (db=%s)", MONGO_DB)
except Exception as e:
	logger.exception("MongoDB connectivity check failed: %s", e)

db = client[MONGO_DB]

account_collection = db["account_transactions"]
card_collection = db["card_transactions"]
results_collection = db["fraud_results"]