import os
import sys

# Add complaint-agent to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'complaint-agent'))

# Force load .env
from dotenv import load_dotenv
load_dotenv()

try:
    from graph.pipeline import complaint_graph
    from models.schemas import ComplaintState
    print("Import successful")
    
    # Test state initialization
    state = ComplaintState(
        user_prompt="I have a problem with my credit card client1",
        customer_id="client1",
        customer_name="John Doe",
        google_access_token=None
    )
    print("Invoking graph...")
    final_state = complaint_graph.invoke(state)
    print("Success!")
    print("Reply:", final_state.get('client_message'))
    
except Exception as e:
    print("AGENT INTERACTION ERROR:", str(e))
    import traceback
    traceback.print_exc()
