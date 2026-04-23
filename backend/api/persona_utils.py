"""
Dynamic Persona Calculation Module
Calculates user persona based on transaction history and balance.
"""

from datetime import datetime
from typing import Dict, Any
from bson import ObjectId


def calculate_persona_from_transactions(transactions: list, balance: float) -> str:
    """
    Calculate user persona based on transaction patterns and balance.
    
    Returns: 'aggressive', 'balanced', or 'conservative'
    """
    if not transactions:
        # Default to balanced for new users
        return 'balanced'
    
    # Analyze transactions
    total_income = 0
    total_expenses = 0
    investment_count = 0
    savings_count = 0
    luxury_spending = 0
    
    for tx in transactions:
        amount = tx.get('amount', 0)
        tx_type = tx.get('type', '')
        category = tx.get('category', '').lower()
        
        if tx_type == 'income':
            total_income += amount
        elif tx_type == 'expense':
            total_expenses += amount
            
            if 'invest' in category or 'bourse' in category or 'action' in category:
                investment_count += 1
            elif 'savings' in category or 'epargne' in category or 'épargne' in category:
                savings_count += 1
            elif 'luxury' in category or 'travel' in category or 'restaurant' in category or 'voyage' in category:
                luxury_spending += amount
    
    # Calculate ratios
    if total_income > 0:
        savings_rate = (total_income - total_expenses) / total_income
    else:
        savings_rate = 0
    
    investment_ratio = investment_count / len(transactions) if transactions else 0
    luxury_ratio = luxury_spending / total_expenses if total_expenses > 0 else 0
    
    # Determine persona based on patterns
    score = 0
    
    # High savings rate -> conservative
    if savings_rate > 0.3:
        score -= 1
    elif savings_rate < 0:
        score += 1
    
    # High investment activity -> aggressive
    if investment_ratio > 0.2:
        score += 2
    elif investment_ratio > 0.1:
        score += 1
    
    # High luxury spending -> aggressive
    if luxury_ratio > 0.3:
        score += 1
    
    # Balance relative to income
    if total_income > 0:
        balance_ratio = balance / total_income
        if balance_ratio > 2:  # High liquidity -> conservative
            score -= 1
        elif balance_ratio < 0.5:  # Low liquidity -> potentially aggressive
            score += 1
    
    # Map score to persona
    if score >= 2:
        return 'aggressive'
    elif score <= -1:
        return 'conservative'
    else:
        return 'balanced'


def seed_user_account_data(user_id: str, name: str) -> Dict[str, Any]:
    """
    Seed initial account data for a new user.
    Creates an account with initial balance and sample transactions.
    """
    from .mongodb import MongoDBClient
    import random
    
    db = MongoDBClient.get_db()
    
    # Generate initial balance (random between 10000 and 100000 TND)
    initial_balance = random.randint(10000, 100000)
    
    # Create account
    account_data = {
        "user_id": user_id,
        "name": name,
        "total_liquidity": initial_balance,
        "monthly_budget": round(initial_balance * 0.1, 2),
        "savings_rate": 20,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    db["accounts"].insert_one(account_data)
    
    # Create sample transactions for persona calculation
    transaction_categories = [
        {"description": "Salaire mensuel", "amount": round(initial_balance * 0.15, 2), "type": "income", "category": "Revenu"},
        {"description": "Loyer", "amount": round(initial_balance * 0.03, 2), "type": "expense", "category": "Logement"},
        {"description": "Courses alimentaires", "amount": round(initial_balance * 0.02, 2), "type": "expense", "category": "Alimentation"},
        {"description": "Factures (électricité, eau)", "amount": round(initial_balance * 0.01, 2), "type": "expense", "category": "Utilités"},
        {"description": "Transport", "amount": round(initial_balance * 0.015, 2), "type": "expense", "category": "Transport"},
    ]
    
    # Add some investment transactions
    if random.random() > 0.5:
        transaction_categories.append({
            "description": "Investissement actions",
            "amount": round(initial_balance * 0.02, 2),
            "type": "expense",
            "category": "Investissement"
        })
    
    # Add some savings
    transaction_categories.append({
        "description": "Épargne mensuelle",
        "amount": round(initial_balance * 0.025, 2),
        "type": "expense",
        "category": "Épargne"
    })
    
    # Insert transactions
    for i, tx in enumerate(transaction_categories):
        tx["user_id"] = user_id
        tx["date"] = datetime.utcnow().isoformat()
        tx["id"] = i + 1
        db["transactions"].insert_one(tx)
    
    # Calculate initial persona
    persona = calculate_persona_from_transactions(transaction_categories, initial_balance)
    
    # Update user with persona
    try:
        db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"persona": persona}}
        )
    except:
        # If user_id is not a valid ObjectId, try as string
        db["users"].update_one(
            {"_id": user_id},
            {"$set": {"persona": persona}}
        )
    
    return {
        "account": account_data,
        "persona": persona,
        "transactions_count": len(transaction_categories)
    }


def update_user_persona(user_id: str) -> str:
    """
    Recalculate and update user persona based on current transactions.
    Call this when new transactions are added.
    """
    from .mongodb import MongoDBClient
    
    db = MongoDBClient.get_db()
    
    # Fetch user transactions
    transactions = list(db["transactions"].find({"user_id": user_id}))
    
    # Fetch user account
    account = db["accounts"].find_one({"user_id": user_id})
    
    balance = 0
    if account:
        balance = account.get("total_liquidity", 0)
    
    # Calculate new persona
    new_persona = calculate_persona_from_transactions(transactions, balance)
    
    # Update user
    try:
        db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"persona": new_persona}}
        )
    except:
        # If user_id is not a valid ObjectId, try as string
        db["users"].update_one(
            {"_id": user_id},
            {"$set": {"persona": new_persona}}
        )
    
    return new_persona
