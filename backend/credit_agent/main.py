from langgraph.graph import StateGraph, END
from state import AgentState
from supervisor.agent import run_supervisor
from finance.agent import run_finance
from risk.agent import run_risk
from decision.agent import run_decision

def supervisor_router(state: AgentState):
    """Router to decide whether to continue to finance or stop."""
    print("====== INSIDE SUPERVISOR ROUTER ======")
    print(f"STATE TYPE: {type(state)}")
    print(f"Validation warnings: {state.get('validation_warnings')}")
    
    if state.get("validation_warnings") and len(state.get("validation_warnings")) > 0:
        print("====== ROUTING TO END ======")
        return "decision"
    print("====== ROUTING TO FINANCE ======")
    return "finance"

def finance_router(state: AgentState):
    """Router to decide whether to continue to risk or stop."""
    print("====== INSIDE FINANCE ROUTER ======")
    fd = state.get("finance_data")
    print(f"finance_data presence: {bool(fd)}")
    if not fd:
        print("====== ROUTING TO END FROM FINANCE ======")
        return "decision"
    print("====== ROUTING TO RISK ======")
    return "risk"

def build_graph():
    # 1. Define the StateGraph
    workflow = StateGraph(AgentState)
    
    # 2. Add nodes
    workflow.add_node("supervisor", run_supervisor)
    workflow.add_node("finance", run_finance)
    workflow.add_node("risk", run_risk)
    workflow.add_node("decision", run_decision)
    
    # 3. Define Entry Point
    workflow.set_entry_point("supervisor")
    
    # 4. Define Edges
    # If supervisor fails, go to Decision to formally deny, else go to FINANCE
    workflow.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "finance": "finance",
            "decision": "decision"
        }
    )
    
    # If finance fails/rejects, go to Decision to formally deny, else go to RISK
    workflow.add_conditional_edges(
        "finance",
        finance_router,
        {
            "risk": "risk",
            "decision": "decision"
        }
    )
    
    workflow.add_edge("risk", "decision")
    workflow.add_edge("decision", END)
    
    # 5. Compile graph
    app = workflow.compile()
    
    return app
