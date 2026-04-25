from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from api import views as api_views
from api import custom_admin

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", custom_admin.admin_dashboard, name="mongo_admin_dashboard"),
    path(
        "admin/<str:collection_name>/",
        custom_admin.admin_collection,
        name="mongo_admin_collection",
    ),
    path(
        "admin/<str:collection_name>/<str:doc_id>/",
        custom_admin.admin_document,
        name="mongo_admin_document",
    ),
    path(
        "admin/<str:collection_name>/<str:doc_id>/delete/",
        custom_admin.admin_delete,
        name="mongo_admin_delete",
    ),
    path("api/", include("api.urls")),

    # Account views
    path("accounts/login/", api_views.mongo_login, name="login"),
    path("accounts/logout/", api_views.mongo_logout, name="logout"),
    path("accounts/dashboard/", api_views.mongo_dashboard, name="dashboard"),
    path("accounts/admin/", api_views.mongo_admin, name="admin"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

