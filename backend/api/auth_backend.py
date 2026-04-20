import bcrypt
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from api.mongodb import get_users_collection


class MongoDBBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        users_collection = get_users_collection()

        # Try to find user by email or phone
        user_doc = users_collection.find_one(
            {"$or": [{"email": username}, {"phone": username}]}
        )

        if not user_doc:
            return None

        # Verify password
        stored_password = user_doc.get("password", "")
        if isinstance(stored_password, str):
            stored_password = stored_password.encode("utf-8")

        try:
            if bcrypt.checkpw(password.encode("utf-8"), stored_password):
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "first_name": user_doc.get("name", "").split()[0]
                        if user_doc.get("name")
                        else "",
                        "last_name": " ".join(user_doc.get("name", "").split()[1:])
                        if user_doc.get("name")
                        else "",
                        "email": user_doc.get("email", ""),
                        "is_staff": user_doc.get("role") in ["admin", "chef of agency"],
                    },
                )
                # Store MongoDB user data in session
                request.session["mongo_user_id"] = str(user_doc.get("_id"))
                request.session["mongo_user_role"] = user_doc.get("role", "customer")
                request.session["mongo_customer_id"] = user_doc.get("customer_id", "")
                return user
        except Exception as e:
            print(f"Auth error: {e}")
            return None

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
