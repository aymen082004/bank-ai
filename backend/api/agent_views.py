

import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_root, "fraud_agent"))
sys.path.append(os.path.join(project_root, "complaint-agent"))
import importlib.util
import jwt
import datetime
import threading

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from dotenv import load_dotenv
from django.http import JsonResponse

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")




# Add paths for agent imports (fraud_agent first so its internal imports resolve)



def load_agent(agent_dir, module_name="agents.react_agent"):
    if 'agents' in sys.modules:
        del sys.modules['agents']
    if 'agents.react_agent' in sys.modules:
        del sys.modules['agents.react_agent']
        
    path = os.path.join(project_root, agent_dir, "agents", "react_agent.py")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

try:
    complaint_agent_module = load_agent("complaint-agent", "complaint_agent_module")
    run_complaint_agent = complaint_agent_module.run_react_agent
    print("[SUCCESS] Complaint agent loaded.")
except Exception as e:
    print(f"[WARNING] Failed to load complaint agent: {e}")
    run_complaint_agent = None

try:
    bank_agent_module = load_agent("reception-agent", "bank_agent_module")
    run_bank_agent = bank_agent_module.run_react_agent
    print("[SUCCESS] Bank agent loaded from 'reception-agent'")
except Exception as e:
    import traceback
    print(f"[ERROR] Failed to load bank agent: {e}")
    traceback.print_exc()
    run_bank_agent = None

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(os.path.join(project_root, "complaint-agent"))

from agents.react_agent import run_react_agent

import jwt
import datetime



@api_view(["POST"])
def complaint_agent_chat(request):
    print(f"[DEBUG] Received request: {request.data}")
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return Response(
            {"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED
        )

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("userId")


        print(f"[DEBUG] User ID: {user_id}")

    except Exception as e:
        return Response(
            {"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED
        )

    message = request.data.get("message")


    print(f"[DEBUG] Message: {message}")

    if not message:
        return Response(
            {"error": "Message required"}, status=status.HTTP_400_BAD_REQUEST
        )

    from .mongodb import get_users_collection
    from bson import ObjectId

    users_collection = get_users_collection()
    user_doc = users_collection.find_one({"_id": ObjectId(user_id)})

    print(f"[DEBUG] User doc: {user_doc}")


    if not user_doc:
        return Response(
            {"error": "User not found in database"}, status=status.HTTP_404_NOT_FOUND
        )

    customer_id = user_doc.get("customer_id")
    google_access_token = user_doc.get("google_access_token")

    try:
        result_holder = [None]
        print(f"[DEBUG] Calling react agent...")
        import threading

        result_holder = [None]

        def run_agent():
            result_holder[0] = run_react_agent(

                user_input=message,
                user_id=user_id,
                customer_id=customer_id,
                google_access_token=google_access_token,
            )

        thread = threading.Thread(target=run_agent)
        thread.daemon = True
        thread.start()
        thread.join(timeout=60)

        if thread.is_alive():


            print("[DEBUG] Agent timeout after 60s")

            return Response(
                {"error": "Agent timeout - took too long"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        agent_result = result_holder[0]

        print(f"[DEBUG] Agent result: {agent_result}")


        if not agent_result:
            return Response(
                {
                    "reply": "Désolé, je n'ai pas pu traiter votre demande. Veuillez réessayer."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "reply": agent_result.get("message", "Réponse non disponible"),
                "details": agent_result.get("details", {})
                if agent_result.get("details")
                else {},
            }
        )

    except Exception as e:

        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def bank_agent_chat(request):
    auth_header = request.headers.get("Authorization")
    print(f"[DEBUG] bank_agent_chat called. Auth header: {'Present' if auth_header else 'Missing'}")
    
    # Manual JWT check (optional but recommended for consistency)
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except Exception as e:
            print(f"[WARNING] Invalid token in bank_agent_chat: {e}")

    message = request.data.get("message")
    if not message:
        return Response({"error": "Message required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        global run_bank_agent
        if run_bank_agent is None:
            print("[DEBUG] run_bank_agent is None, trying to re-load...")
            bank_agent_module = load_agent("reception-agent", "bank_agent_module")
            run_bank_agent = bank_agent_module.run_react_agent
            
        print(f"[DEBUG] Running bank agent for message: {message[:50]}...")
        result = run_bank_agent(message)
        print(f"[DEBUG] Bank agent execution successful.")
        if isinstance(result, dict):
            return JsonResponse({
                "answer": result.get("answer", "Erreur"),
                "rationale": result.get("rationale", ""),
                "status": "success"
            })
        else:
            return JsonResponse({"answer": str(result), "status": "success"})
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] bank_agent_chat failed: {str(e)}\n{error_trace}")
        return JsonResponse({"error": str(e), "trace": error_trace}, status=500)

@api_view(['GET'])
def get_bank_memory(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    token = auth_header.split(" ")[1]
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)

    print(f"[DEBUG] get_bank_memory called with valid token")
    try:
        # Dynamic import due to hyphen in 'reception-agent'
        storage_path = os.path.join(project_root, "reception-agent", "agents", "agent_storage.py")
        print(f"[DEBUG] Loading storage from: {storage_path}")
        spec = importlib.util.spec_from_file_location("bank_agent_storage", storage_path)
        agent_storage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_storage)
        
        limit = int(request.GET.get("limit", 50))
        events = agent_storage.load_recent_events(limit=limit, default_path=agent_storage.CHAT_HISTORY_FILE)
        print(f"[DEBUG] Successfully loaded {len(events)} events from {agent_storage.CHAT_HISTORY_FILE}")
        return JsonResponse(events, safe=False)
    except Exception as e:
        print(f"[ERROR] get_bank_memory error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['POST'])
def new_bank_session(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    token = auth_header.split(" ")[1]
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)

    try:
        storage_path = os.path.join(project_root, "reception-agent", "agents", "agent_storage.py")
        spec = importlib.util.spec_from_file_location("bank_agent_storage", storage_path)
        agent_storage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_storage)
        
        agent_storage.save_new_session("chat")
        agent_storage.save_new_session("action")
        return JsonResponse({"status": "ok", "new_session": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['POST'])
def clear_bank_memory(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    token = auth_header.split(" ")[1]
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)

    try:
        storage_path = os.path.join(project_root, "reception-agent", "agents", "agent_storage.py")
        spec = importlib.util.spec_from_file_location("bank_agent_storage", storage_path)
        agent_storage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_storage)
        
        agent_storage.clear_memory("chat")
        agent_storage.clear_memory("action")
        return JsonResponse({"status": "ok", "cleared": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

        import traceback

        print("AGENT INTERACTION ERROR:", str(e))
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(["POST"])
def fraud_agent_chat(request):
    print(f"[DEBUG] Received fraud request: {request.data}")
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return Response(
            {"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED
        )

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("userId")
        print(f"[DEBUG] User ID: {user_id}")
    except Exception as e:
        return Response(
            {"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED
        )

    message = request.data.get("message")
    client_id = request.data.get("client_id")
    print(f"[DEBUG] Message: {message}, Client ID: {client_id}")

    if not message and not client_id:
        return Response(
            {"error": "Message or client_id required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        print(f"[DEBUG] Calling fraud agent...")

        from fraud_agent.agent.simple_text_agent import fraud_agent_text

        query = message if message else f"Check fraud for {client_id}"
        result = fraud_agent_text(query)

        print(f"[DEBUG] Fraud agent result: {result}")

        if "error" in result:
            return Response(
                {"reply": f"Erreur lors de l'analyse: {result['error']}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Helper to clean markdown and duplicates
        def clean_text(text, decision=None, confidence=None):
            if not text:
                return "N/A"
            import re
            # Remove markdown
            text = re.sub(r'\*\*+', '', text)
            text = re.sub(r'#{1,6}\s*', '', text)
            text = re.sub(r'^[\s]*[-*]\s+', '', text, flags=re.MULTILINE)
            text = re.sub(r'\*+', '', text)
            # Remove lines that just repeat decision/confidence/score
            lines = text.split('\n')
            cleaned_lines = []
            for line in lines:
                line_lower = line.lower().strip()
                # Skip repetitive metadata lines
                if decision and 'decision' in line_lower and decision.lower() in line_lower:
                    if len(line.strip()) < 50:
                        continue
                if 'confiance' in line_lower and confidence:
                    if len(line.strip()) < 40:
                        continue
                if 'score total' in line_lower or 'score de risque' in line_lower:
                    continue
                if line.strip() and line.strip() not in cleaned_lines:
                    cleaned_lines.append(line.strip())
            return '\n'.join(cleaned_lines).strip() or "N/A"

        bank_report = result.get("bank_report", {})
        decision = bank_report.get('final_decision') or result.get('decision', 'Inconnue')
        confidence = bank_report.get('final_confidence') or result.get('confidence', 0)

        # Build response with explanation
        if bank_report.get("final_decision") and bank_report.get('summary'):
            summary = clean_text(bank_report.get('summary', 'N/A'), decision, confidence)
            action = clean_text(bank_report.get('recommended_action', 'N/A'), decision, confidence)
            reply_text = f"Analyse de Fraude - {result.get('client_id', 'Client')}\n\n"
            reply_text += f"Décision: {decision}\n"
            reply_text += f"Confiance: {confidence:.0%}\n\n"
            if action and action != "N/A":
                reply_text += f"Action recommandée: {action}\n\n"
            reply_text += f"Explication:\n{summary}"
        else:
            explanation = clean_text(result.get('final_explanation', 'N/A'), decision, confidence)
            reply_text = f"Analyse de Fraude - {result.get('client_id', 'Client')}\n\n"
            reply_text += f"Décision: {decision}\n"
            reply_text += f"Confiance: {confidence:.0%}\n\n"
            reply_text += f"Explication:\n{explanation}"

        return Response(
            {
                "reply": reply_text,
                "details": {
                    "client_id": result.get("client_id"),
                    "decision": result.get("decision"),
                    "confidence": result.get("confidence"),
                    "total_risk_score": result.get("total_risk_score"),
                    "account": result.get("account"),
                    "card": result.get("card"),
                    "bank_report": bank_report,
                }
            }
        )

    except Exception as e:
        import traceback

        print("FRAUD AGENT ERROR:", str(e))
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
