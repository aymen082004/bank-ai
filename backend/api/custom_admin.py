from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from .mongodb import MongoDBClient


def get_db():
    return MongoDBClient.get_db()


def check_mongo_auth(request):
    """Check if user is logged in via MongoDB session."""
    return request.session.get("mongo_user_id")


def doc_to_dict(doc):
    """Convert MongoDB document to dict with string ID."""
    if doc is None:
        return {}
    d = {"doc_id": str(doc.get("_id", ""))}
    for key, val in doc.items():
        if key == "_id":
            d["doc_id"] = str(val)
        elif key == "google_access_token":
            d[key] = "Yes" if val else "No"
        elif key == "picture":
            d[key] = (
                f"<img src='{val}' width='40' height='40' style='border-radius:50%'>"
                if val
                else "No"
            )
        elif isinstance(val, (dict, list)):
            d[key] = str(val)
        else:
            d[key] = val
    return d


def doc_to_dict_edit(doc):
    """Convert MongoDB document for editing - original values."""
    if doc is None:
        return {}
    d = {}
    for key, val in doc.items():
        if key == "_id":
            d["doc_id"] = str(val)
        else:
            d[key] = val if val is not None else ""
    return d


# Default fields - will be dynamically discovered
COLLECTIONS = {}


@csrf_exempt
def admin_dashboard(request):
    if not check_mongo_auth(request):
        return redirect("/accounts/login/")

    db = get_db()
    role = request.session.get("mongo_user_role", "")
    customer_id = request.session.get("mongo_customer_id", "")

    # Customers see only their data, chef/admin see all
    is_customer = role == "customer" and customer_id

    if is_customer and customer_id:
        try:
            stats = {
                "accounts": db.accounts.count_documents({"customer_id": customer_id}),
                "transactions": db.bank_transactions.count_documents(
                    {"customer_id": customer_id}
                ),
                "bookings": db.bookings.count_documents({"customer_id": customer_id}),
                "reclamations": db.reclamations.count_documents(
                    {"customer_id": customer_id}
                ),
            }
        except:
            stats = {}

        collections = [
            "accounts",
            "bank_transactions",
            "bookings",
            "reclamations",
        ]
    else:
        try:
            stats = {
                "customers": db.customers.count_documents({}),
                "accounts": db.accounts.count_documents({}),
                "transactions": db.bank_transactions.count_documents({}),
                "cheques": db.cheques.count_documents({}),
                "reclamations": db.reclamations.count_documents({"status": "pending"}),
                "bookings": db.bookings.count_documents({}),
                "loans": db.recovery_loans.count_documents({}),
                "users": db.users.count_documents({}),
            }
        except:
            stats = {}

        collections = [
            "customers",
            "accounts",
            "bank_transactions",
            "cheques",
            "reclamations",
            "bookings",
            "recovery_loans",
            "users",
            "bank_params",
        ]

    return render(
        request,
        "custom_admin/dashboard.html",
        {
            "collections": collections,
            "stats": stats,
            "user_role": role,
        },
    )


@csrf_exempt
def admin_collection(request, collection_name):
    if not check_mongo_auth(request):
        return redirect("/accounts/login/")

    role = request.session.get("mongo_user_role", "")
    customer_id = request.session.get("mongo_customer_id", "")
    is_customer = role == "customer"

    # Restrict customer to only these collections
    if is_customer and collection_name not in (
        "accounts",
        "bank_transactions",
        "bookings",
        "reclamations",
    ):
        return redirect("/admin/")
    customer_id = request.session.get("mongo_customer_id", "")
    is_customer = role == "customer"

    per_page = int(request.GET.get("limit", 20))
    page = int(request.GET.get("page", 1))
    search = request.GET.get("search", "")

    # Build query filter
    query_filter = {}
    if is_customer and customer_id:
        query_filter = {"customer_id": customer_id}

    try:
        sample = get_db()[collection_name].find_one(query_filter)
        fields = [k for k in sample.keys() if k != "_id"] if sample else []

        if search:
            query_filter["customer_id"] = {"$regex": search, "$options": "i"}

        docs = [
            doc_to_dict(d)
            for d in get_db()[collection_name]
            .find(query_filter)
            .skip((page - 1) * per_page)
            .limit(per_page)
        ]

        total = get_db()[collection_name].count_documents(query_filter)
    except Exception as e:
        print(f"Error: {e}")
        docs = []
        total = 0
        fields = []

    # Pagination
    start = (page - 1) * per_page
    end = start + per_page

    return render(
        request,
        "custom_admin/collection.html",
        {
            "collection_name": collection_name,
            "fields": fields,
            "docs": docs,
            "total": total,
            "page": page,
            "per_page": per_page,
            "search": search,
            "has_prev": page > 1,
            "has_next": (page * per_page) < total,
            "prev_page": page - 1,
            "next_page": page + 1,
            "user_role": role,
        },
    )


@csrf_exempt
def admin_document(request, collection_name, doc_id):
    if not check_mongo_auth(request):
        return redirect("/accounts/login/")

    role = request.session.get("mongo_user_role", "")

    from bson import ObjectId

    try:
        doc = get_db()[collection_name].find_one({"_id": ObjectId(doc_id)})
        fields = [k for k in doc.keys() if k != "_id"] if doc else []
    except:
        doc = None
        fields = []

    if request.method == "POST":
        form_data = {}
        for key in fields:
            if key not in ("_id", "picture", "google_access_token"):
                val = request.POST.get(key, "")
                form_data[key] = val
        get_db()[collection_name].update_one(
            {"_id": ObjectId(doc_id)}, {"$set": form_data}
        )
        doc = get_db()[collection_name].find_one({"_id": ObjectId(doc_id)})
        fields = [k for k in doc.keys() if k != "_id"] if doc else []
        return render(
            request,
            "custom_admin/document.html",
            {
                "collection_name": collection_name,
                "fields": fields,
                "doc": doc_to_dict_edit(doc) if doc else {},
                "doc_id": doc_id,
                "saved": True,
                "user_role": role,
            },
        )

    return render(
        request,
        "custom_admin/document.html",
        {
            "collection_name": collection_name,
            "fields": fields,
            "doc": doc_to_dict_edit(doc) if doc else {},
            "doc_id": doc_id,
            "user_role": role,
        },
    )


@csrf_exempt
def admin_delete(request, collection_name, doc_id):
    if not check_mongo_auth(request):
        return redirect("/accounts/login/")

    from bson import ObjectId

    deleted = False

    if request.method == "POST":
        try:
            get_db()[collection_name].delete_one({"_id": ObjectId(doc_id)})
            deleted = True
        except:
            pass

    return render(
        request,
        "custom_admin/delete.html",
        {
            "collection_name": collection_name,
            "doc_id": doc_id,
            "deleted": deleted,
        },
    )
