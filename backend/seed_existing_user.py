"""
Script to seed data for existing user abbassi20290@gmail.com
Run: python seed_existing_user.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from api.persona_utils import seed_user_account_data, update_user_persona
from api.mongodb import get_users_collection, MongoDBClient


def seed_existing_user(email):
    """Seed account and transaction data for an existing user."""
    users_collection = get_users_collection()
    
    # Find user by email
    user = users_collection.find_one({"email": email})
    if not user:
        print(f"❌ User not found: {email}")
        return False
    
    user_id = str(user["_id"])
    name = user.get("name", "User")
    
    print(f"✅ Found user: {name} ({email})")
    print(f"   User ID: {user_id}")
    
    # Check if user already has account data
    db = MongoDBClient.get_db()
    existing_account = db["accounts"].find_one({"user_id": user_id})
    
    if existing_account:
        print(f"⚠️  User already has account data. Updating persona only...")
        # Just recalculate persona based on existing transactions
        new_persona = update_user_persona(user_id)
        print(f"✅ Updated persona to: {new_persona}")
    else:
        # Seed fresh data
        print(f"🌱 Seeding account and transaction data...")
        try:
            seeded_data = seed_user_account_data(user_id, name)
            print(f"✅ Successfully seeded data:")
            print(f"   - Initial balance: {seeded_data['account']['total_liquidity']} TND")
            print(f"   - Monthly budget: {seeded_data['account']['monthly_budget']} TND")
            print(f"   - Transactions: {seeded_data['transactions_count']}")
            print(f"   - Calculated persona: {seeded_data['persona']}")
            
            # Update user with persona
            users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"persona": seeded_data["persona"]}}
            )
            print(f"✅ Updated user persona in database")
            
        except Exception as e:
            print(f"❌ Error seeding data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Seeding data for existing user")
    print("=" * 60)
    
    email = "dridi.yassine.1@esprit.tn"
    success = seed_existing_user(email)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Seeding completed successfully!")
        print("=" * 60)
        print(f"\nUser {email} now has:")
        print("  - Account with balance and budget")
        print("  - Sample transaction history")
        print("  - Dynamic persona (aggressive/balanced/conservative)")
        print("\nRefresh the 'Agent Recommandation' dashboard to see the data!")
    else:
        print("\n❌ Seeding failed")
        sys.exit(1)
