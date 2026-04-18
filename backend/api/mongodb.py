import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

class MongoDBClient:
    _client = None

    @classmethod
    def get_db(cls):
        if cls._client is None:
            uri = os.getenv('MONGO_URI')
            cls._client = MongoClient(uri)
        return cls._client['bank_ai']

def get_users_collection():
    db = MongoDBClient.get_db()
    return db['users']

def get_customers_collection():
    db = MongoDBClient.get_db()
    return db['customers']
