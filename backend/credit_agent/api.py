import os
import tempfile
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from supervisor.bd.mcp_server import mcp_handle

# Import LangGraph workflow
from main import build_graph
from langgraph.types import Command

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Compile the LangGraph workflow globally to avoid recompiling on every request
workflow = build_graph()

def format_agent_response(state):
    """Utility to extract key information from the final graph state."""
    final_decision = state.get("final_decision", "")
    validation_warnings = state.get("validation_warnings", [])
    
    # If the decision was rejected early by the supervisor, or a final decision exists
    return {
        "status": "success",
        "validation_warnings": validation_warnings,
        "final_decision": final_decision,
        "supervisor_info": state.get("client_info", ""),
        "finance_report": state.get("finance_report", ""),
        "risk_report": state.get("risk_report", "")
    }

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "API is running"}), 200

@app.route('/bank_params', methods=['GET'])
def bank_params():
    try:
        req = {
            "action": "fetch",
            "collection": "bank_params",
            "filter": {"param_type": "global_rates"}
        }
        resp = mcp_handle(req)
        if resp and resp.get("status") == "success" and resp.get("data"):
            data = resp.get("data")[0]
            data["_id"] = str(data["_id"])
            return jsonify(data), 200
    except Exception as e:
        print(f"Failed to fetch bank_params from MCP: {e}")
        
    # Default values
    return jsonify({
        "tmm": 0.0699,
        "marge_additionnelle_consommation": 0.05,
        "marge_additionnelle_amenagement": 0.0375,
        "marge_additionnelle_voiture": 0.035
    }), 200


@app.route('/process_credit', methods=['POST'])
def process_credit():
    # 1. Parse incoming multiform-data
    client_id = request.form.get("client_id", "API_Client")
    type_credit = request.form.get("type_credit")
    
    if not type_credit:
         return jsonify({"status": "error", "message": "Missing 'type_credit' parameter"}), 400
         
    try:
        amount = float(request.form.get("amount", 0.0))
        repayment_period = int(request.form.get("repayment_period", 12))
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid 'amount' or 'repayment_period'"}), 400

    # 2. Handle PDF Upload
    if 'fiche_paie' not in request.files:
        return jsonify({"status": "error", "message": "Missing 'fiche_paie' file in the form data"}), 400
        
    file = request.files['fiche_paie']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"status": "error", "message": "The uploaded file must be a PDF"}), 400

    # Save to a temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(temp_fd, 'wb') as f:
        file.save(f)

    # Allow custom details to be sent as JSON string in form data
    details_str = request.form.get("details_json", "{}")
    try:
        details_dict = json.loads(details_str)
    except json.JSONDecodeError:
        details_dict = {}

    details_dict["fiche_paie_path"] = temp_path

    # 3. Construct the Initial State for LangGraph
    initial_state = {
        "client_id": client_id,
        "type_credit": type_credit,
        "amount": amount,
        "repayment_period": repayment_period,
        "details": details_dict,
        
        # Initialize empty states
        "messages": [],
        "validation_warnings": [],
        "client_info": "",
        "accounts_info": {},
        "structured_request": {},
        "finance_data": {},
        "finance_report": "",
        "risk_report": "",
        "final_decision": ""
    }

    # 4. Execute the Graph
    print(f"--- Starting workflow for {client_id}: {type_credit} ({amount} TND over {repayment_period} months) ---")
    
    try:
        final_state = workflow.invoke(initial_state)
        response_payload = format_agent_response(final_state)
        
        # Cleanup temp file
        try:
            os.remove(temp_path)
        except Exception as e:
            print(f"Warning: Could not remove temporary file {temp_path}: {e}")
            
        return jsonify(response_payload), 200

    except Exception as e:
        import traceback
        print(f"API Error Occurred:\n{traceback.format_exc()}")
        # Cleanup temp file on error
        try:
            os.remove(temp_path)
        except Exception:
            pass
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    # Run the Flask app on default port 5000 (accessible on local network)
    # Debug = True causes auto-reload on file changes
    app.run(host='0.0.0.0', port=5000, debug=True)
