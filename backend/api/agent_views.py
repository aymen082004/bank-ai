from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from dotenv import load_dotenv
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(os.path.join(project_root, "complaint-agent"))

from agents.react_agent import run_react_agent

import jwt
import datetime

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")


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
        import traceback

        print("AGENT INTERACTION ERROR:", str(e))
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
