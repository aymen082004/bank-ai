from mcp_server import mcp_handle

# Fetch client
message_fetch = {
    "action": "fetch",
    "collection": "customers",
    "filter": {"personal_info.age": 59}
}

result = mcp_handle(message_fetch)
print(result)

# Update client
message_update = {
    "action": "update",
    "collection": "customers",
    "filter": {"personal_info.age": 59},
    "data": {"employment.annual_income": 25000}
}

result = mcp_handle(message_update)
print(result)

# Insert client
message_insert = {
    "action": "insert",
    "collection": "customers",
    "data": {
        "personal_info": {"nom":"Test","prenom":"MCP","age":30,"genre":"F"},
        "employment": {"annual_income":30000,"monthly_income":2500,"employment_status":"Employed","debt_to_income_ratio":0.05},
        "credit_profile": {},
        "loans": [],
        "transactions": []
    }
}

result = mcp_handle(message_insert)
print(result)