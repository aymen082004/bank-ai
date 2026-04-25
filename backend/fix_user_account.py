from api.mongodb import MongoDBClient

db = MongoDBClient.get_db()

# Update the account with the wrong user_id to the correct one
result = db.accounts.update_one(
    {'user_id': '69ea3a6489e3b1bca4412bdb'}, 
    {'$set': {'user_id': '69ea3d8389e3b1bca4412bdc'}}
)

print(f'Updated {result.modified_count} account(s)')

# Also update transactions
result2 = db.transactions.update_many(
    {'user_id': '69ea3a6489e3b1bca4412bdb'},
    {'$set': {'user_id': '69ea3d8389e3b1bca4412bdc'}}
)

print(f'Updated {result2.modified_count} transaction(s)')

# Verify
account = db.accounts.find_one({'user_id': '69ea3d8389e3b1bca4412bdc'})
if account:
    print(f'✅ Account found: Balance = {account.get("total_liquidity")} TND')
else:
    print('❌ Account not found')
