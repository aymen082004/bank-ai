from django.urls import path
from . import views, agent_views

urlpatterns = [
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/google/', views.google_auth, name='google_auth'),
    path('agents/complaint/', agent_views.complaint_agent_chat, name='complaint_agent_chat'),
]
