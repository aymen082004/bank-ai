from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, START, END

# import pi_agents
from .pi_agents.registration import registration_agent
from .pi_agents.behavior import behavior_agent
from .pi_agents.router import router_agent
from .pi_agents.scraper import scraper_agent
from .pi_agents.stock import stock_agent
from .pi_agents.recommendation import recommendation_agent
from .pi_agents.xai import xai_agent
from .pi_agents.execution import execution_agent

# Define the state
class BankState(TypedDict):
    user_id: str
    user_input: str
    profile: dict
    persona: str
    listings: List[dict]
    stocks: List[dict]
    recommendations: List[dict]
    explanation: str
    executed: bool

def create_graph():
    """
    Creates the LangGraph Agentic Flow.
    """
    workflow = StateGraph(BankState)

    # Add Nodes
    workflow.add_node("registration", registration_agent)
    workflow.add_node("behavior", behavior_agent)
    workflow.add_node("scraper", scraper_agent)
    workflow.add_node("stock", stock_agent)
    workflow.add_node("recommendation", recommendation_agent)
    workflow.add_node("xai", xai_agent)
    workflow.add_node("execution", execution_agent)

    # Add Edges
    workflow.add_edge(START, "registration")
    workflow.add_edge("registration", "behavior")
    
    # Conditional Routing using the router agent
    def decide_route(state):
        route = router_agent(state)
        if route == "scraper":
            return "scraper"
        elif route == "stock":
            return "stock"
        else:
            return END

    workflow.add_conditional_edges(
        "behavior",
        decide_route,
        {
            "scraper": "scraper",
            "stock": "stock",
            END: END
        }
    )

    workflow.add_edge("scraper", "recommendation")
    workflow.add_edge("stock", "recommendation")
    workflow.add_edge("recommendation", "xai")
    workflow.add_edge("xai", "execution")
    workflow.add_edge("execution", END)

    return workflow.compile()

# Initialize the graph app at module level for use by API views
app = create_graph()

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Example 1: Tunisian dialect car search
    initial_state_car = {
        "user_id": "user_123",
        "user_input": "نحب نشري كرهبة ب 30 مليون",
        "profile": {},
        "persona": "neutral",
        "listings": [],
        "stocks": [],
        "recommendations": [],
        "explanation": "",
        "executed": False
    }
    
    # Example 2: Stock search
    initial_state_stock = {
        "user_id": "user_456",
        "user_input": "Search for Apple stock details",
        "profile": {},
        "persona": "spender",
        "listings": [],
        "stocks": [],
        "recommendations": [],
        "explanation": "",
        "executed": False
    }
    
    # Run the system for car
    print("🚀 Starting Agentic Digital Bank Pipeline (Car Search)...")
    final_state_car = app.invoke(initial_state_car)
    
    print("\n--- CAR RECOMMENDATIONS ---")
    for rec in final_state_car.get("recommendations", []):
        print(f"Asset: {rec['asset']} | Decision: {rec['decision']} | Reason: {rec['reason']}")

    # Run the system for stock
    print("\n🚀 Starting Agentic Digital Bank Pipeline (Stock Search)...")
    final_state_stock = app.invoke(initial_state_stock)
    
    print("\n--- STOCK DETAILS & SEARCH RESULTS ---")
    for s in final_state_stock.get("stocks", []):
        print(f"Symbol: {s['symbol']} | Name: {s['name']} | Price: ${s['price']} | Trend: {s['trend']}")
        if 'description' in s:
            print(f"Description: {s['description'][:100]}...")
        if 'related_companies' in s:
            print(f"Related: {', '.join(s['related_companies'])}")
        
    print("\n--- RECOMMENDATION (XAI) ---")
    print(final_state_stock.get("explanation"))
    
    print("\n✅ Execution simulated and data persisted in MongoDB + Neo4j.")
