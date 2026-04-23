"""
Check user data in MongoDB
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from api.mongodb import MongoDBClient

def check_user(user_id, email):
    db = MongoDBClient.get_db()
    
    print(f"\n=== Checking user: {user_id} / {email} ===\n")
    
    # Check users collection
    user = db["users"].find_one({"email": email})
    if user:
        print(f"✅ Found user in 'users' collection:")
        print(f"   _id: {user['_id']}")
        print(f"   email: {user.get('email')}")
        print(f"   name: {user.get('name')}")
        print(f"   persona: {user.get('persona')}")
    else:
        print(f"❌ User not found in 'users' collection")
    
    # Check accounts by user_id string
    account = db["accounts"].find_one({"user_id": user_id})
    if account:
        print(f"\n✅ Found account by user_id string:")
        print(f"   user_id: {account.get('user_id')}")
        print(f"   total_liquidity: {account.get('total_liquidity')}")
    else:
        print(f"\n❌ No account found with user_id='{user_id}'")
        
    # Check accounts by ObjectId
    from bson import ObjectId
    try:
        account_oid = db["accounts"].find_one({"user_id": ObjectId(user_id)})
        if account_oid:
            print(f"\n✅ Found account with ObjectId:")
            print(f"   user_id: {account_oid.get('user_id')}")
    except:
        pass
    
    # List all accounts
    print(f"\n--- All accounts in database ---")
    for acc in db["accounts"].find():
        print(f"   user_id: {acc.get('user_id')} - Balance: {acc.get('total_liquidity')}")
    
    # List all users
    print(f"\n--- All users in database ---")
    for u in db["users"].find():
        print(f"   _id: {u['_id']} - {u.get('email')} - {u.get('name')}")

if __name__ == "__main__":
    # Check the user from the error logs
    check_user("69ea3d8389e3b1bca4412bdc", "abbassi20290@gmail.com")
