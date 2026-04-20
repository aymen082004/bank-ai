from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
import bcrypt
import jwt
import os
from dotenv import load_dotenv
import datetime
from google.oauth2 import id_token
from google.auth.transport import requests
from django.shortcuts import redirect

from .mongodb import get_users_collection, get_customers_collection

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


def generate_jwt(user_dict):
    payload = {
        "userId": str(user_dict["_id"]),
        "role": user_dict.get("role", ""),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@csrf_exempt
@api_view(["POST"])
def register(request):
    data = request.data
    name = data.get("name")
    phone = data.get("phone")
    email = data.get("email", "")
    cin = data.get("cin", "")
    role = "customer"

    if not name or not (phone or email):
        return Response(
            {"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST
        )

    users_collection = get_users_collection()
    customers_collection = get_customers_collection()

    if email and users_collection.find_one({"email": email}):
        return Response(
            {"error": "User already exists with this email"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if phone and users_collection.find_one({"phone": phone}):
        return Response(
            {"error": "User already exists with this phone number"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    new_user = {
        "name": name,
        "phone": phone,
        "email": email,
        "cin": cin,
        "role": role,
        "created_at": datetime.datetime.utcnow(),
    }

    if cin:
        customer = customers_collection.find_one({"personal_info.cin": cin})
        if customer:
            new_user["customer_id"] = str(customer["_id"])

    result = users_collection.insert_one(new_user)
    new_user["_id"] = result.inserted_id

    token = generate_jwt(new_user)

    return Response(
        {
            "token": token,
            "user": {
                "id": str(new_user["_id"]),
                "name": name,
                "role": role,
                "email": email,
                "cin": new_user.get("cin", ""),
                "customer_id": new_user.get("customer_id", ""),
                "picture": new_user.get("picture", ""),
            },
        },
        status=status.HTTP_201_CREATED,
    )


@csrf_exempt
@api_view(["POST"])
def login(request):
    data = request.data
    email = data.get("email") or data.get("identifier")
    cin = data.get("cin") or data.get("password")

    users_collection = get_users_collection()

    if not email or not cin:
        return Response(
            {"error": "Email and CIN are required"}, status=status.HTTP_400_BAD_REQUEST
        )

    user = users_collection.find_one({"email": email})

    if not user:
        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )

    stored_cin = str(user.get("cin", ""))
    input_cin = str(cin)

    if stored_cin != input_cin:
        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )

    token = generate_jwt(user)

    return Response(
        {
            "token": token,
            "user": {
                "id": str(user["_id"]),
                "name": user.get("name"),
                "role": user.get("role"),
                "email": user.get("email", ""),
                "cin": user.get("cin", ""),
                "customer_id": user.get("customer_id", ""),
                "picture": user.get("picture", ""),
            },
        },
        status=status.HTTP_200_OK,
    )


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def google_auth(request):
    data = request.data
    token = data.get("token")

    try:
        import requests as httprequests

        user_info_response = httprequests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )

        if user_info_response.status_code != 200:
            return Response(
                {"error": "Invalid Google token"}, status=status.HTTP_401_UNAUTHORIZED
            )

        idinfo = user_info_response.json()
        google_id = idinfo.get("sub")
        email = idinfo.get("email", "")
        name = idinfo.get("name", "")
        picture = idinfo.get("picture", "")
        google_access_token = token

        users_collection = get_users_collection()
        customers_collection = get_customers_collection()

        query = [{"googleId": google_id}]
        if email:
            query.append({"email": email})

        user = users_collection.find_one({"$or": query})

        role = "customer"
        phone = data.get("phone")
        cin = data.get("cin", "")

        if not user:
            if not phone or not cin:
                return Response(
                    {
                        "requiresRole": True,
                        "email": email,
                        "name": name,
                        "picture": picture,
                    },
                    status=status.HTTP_200_OK,
                )

            new_user = {
                "googleId": google_id,
                "email": email,
                "name": name,
                "role": role,
                "phone": phone,
                "cin": cin,
                "google_access_token": google_access_token,
                "picture": picture,
                "created_at": datetime.datetime.utcnow(),
            }

            if cin:
                customer = customers_collection.find_one({"personal_info.cin": cin})
                if customer:
                    new_user["customer_id"] = str(customer["_id"])

            result = users_collection.insert_one(new_user)
            new_user["_id"] = result.inserted_id
            user = new_user
        else:
            update_data = {}
            if not user.get("googleId"):
                update_data["googleId"] = google_id
            if not user.get("picture"):
                update_data["picture"] = picture
            if not user.get("email"):
                update_data["email"] = email
            update_data["google_access_token"] = google_access_token

            if update_data:
                users_collection.update_one({"_id": user["_id"]}, {"$set": update_data})
                user.update(update_data)

        auth_token = generate_jwt(user)
        return Response(
            {
                "token": auth_token,
                "user": {
                    "id": str(user["_id"]),
                    "name": user.get("name"),
                    "role": user.get("role"),
                    "email": user.get("email", ""),
                    "cin": user.get("cin", ""),
                    "customer_id": user.get("customer_id", ""),
                    "picture": user.get("picture", ""),
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": "Exception during Google Auth verification"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


from django.shortcuts import render, redirect
from django.contrib.auth import authenticate
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from .mongodb import get_users_collection


@csrf_exempt
def mongo_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        cin = request.POST.get("cin")

        users_collection = get_users_collection()

        # Find user by exact email
        user_doc = users_collection.find_one({"email": email})

        # Try by name
        if not user_doc:
            user_doc = users_collection.find_one(
                {"name": {"$regex": f"^{email}$", "$options": "i"}}
            )

        # Debug: print what we found
        print(f"DEBUG - Email: {email}, Found: {user_doc}")

        if user_doc:
            stored_cin = user_doc.get("cin")
            print(
                f"DEBUG - Stored CIN: {stored_cin}, Input CIN: {cin}, Match: {stored_cin == cin}"
            )

        # Check if user exists and CIN matches (compare as strings)
        user_cin = str(user_doc.get("cin", "")) if user_doc.get("cin") else ""
        input_cin = str(cin) if cin else ""

        if user_doc and user_cin == input_cin:
            request.session["mongo_user_id"] = str(user_doc.get("_id"))
            request.session["mongo_user_role"] = user_doc.get("role", "customer")
            request.session["mongo_customer_id"] = user_doc.get("customer_id", "")
            request.session["mongo_user_name"] = user_doc.get("name", "")
            request.session["mongo_user_email"] = user_doc.get("email", "")
            request.session["mongo_user_picture"] = user_doc.get("picture", "")
            return redirect("/admin/")

        messages.error(request, "Email ou CIN incorrect. Check your credentials.")
        return render(request, "accounts/login.html")

    return render(request, "accounts/login.html")


def mongo_dashboard(request):
    # Check MongoDB session instead of Django auth
    if not request.session.get("mongo_user_id"):
        return redirect("/accounts/login/")

    role = request.session.get("mongo_user_role", "customer")
    name = request.session.get("mongo_user_name", "")

    # Restrict admin access to chef/agency only
    if role not in ["chef", "admin", "agency"] and "chef" not in role.lower():
        return redirect("/accounts/login/")
    user_id = request.session.get("mongo_user_id", "")
    customer_id = request.session.get("mongo_customer_id", "")

    # Get user's complaints from MongoDB
    from .mongodb import MongoDBClient

    db = MongoDBClient.get_db()
    reclamations = (
        list(db["reclamations"].find({"customer_id": customer_id}))
        if customer_id
        else []
    )
    bookings = (
        list(db["bookings"].find({"customer_id": customer_id})) if customer_id else []
    )

    context = {
        "user": request.user,
        "name": name,
        "role": role,
        "user_id": user_id,
        "customer_id": customer_id,
        "reclamations": reclamations,
        "bookings": bookings,
    }

    return render(request, "accounts/dashboard.html", context)


from bson import ObjectId


def mongo_admin(request):
    if not request.user.is_authenticated:
        return redirect("/accounts/login/")

    role = request.session.get("mongo_user_role", "customer")
    if role not in ["admin", "chef of agency"]:
        return redirect("/accounts/dashboard/")

    collection_name = request.GET.get("collection", "users")
    search_query = request.GET.get("search", "")

    from .mongodb import MongoDBClient

    db = MongoDBClient.get_db()

    # Get documents from MongoDB
    collection = db[collection_name]

    if search_query:
        # Search in all string fields
        documents = list(
            collection.find(
                {
                    "$or": [
                        {k: {"$regex": search_query, "$options": "i"}}
                        for k in [
                            "name",
                            "email",
                            "phone",
                            "role",
                            "customer_id",
                            "complaint",
                            "summary",
                        ]
                    ]
                }
            ).limit(100)
        )
    else:
        documents = list(collection.find().limit(100))

    # Convert ObjectId to string for display
    for doc in documents:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])

    context = {
        "user": request.user,
        "collection": collection_name,
        "documents": documents,
        "search": search_query,
    }

    return render(request, "accounts/admin.html", context)


def mongo_logout(request):
    # Clear MongoDB session
    keys = [
        "mongo_user_id",
        "mongo_user_role",
        "mongo_customer_id",
        "mongo_user_name",
        "mongo_user_email",
    ]
    for key in keys:
        request.session.pop(key, None)
    return redirect("/accounts/login/")
