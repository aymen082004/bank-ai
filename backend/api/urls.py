from django.urls import path
from . import views, agent_views, transcription_views

urlpatterns = [
    path("auth/register/", views.register, name="register"),
    path("auth/login/", views.login, name="api_login"),
    path("auth/google/", views.google_auth, name="google_auth"),
    path(
        "agents/complaint/",
        agent_views.complaint_agent_chat,
        name="complaint_agent_chat",
    ),
    path("agents/bank/", agent_views.bank_agent_chat, name="bank_agent_chat"),
    path("agents/bank/memory/", agent_views.get_bank_memory, name="get_bank_memory"),
    path(
        "agents/bank/new-session/",
        agent_views.new_bank_session,
        name="new_bank_session",
    ),
    path(
        "agents/bank/clear-memory/",
        agent_views.clear_bank_memory,
        name="clear_bank_memory",
    ),
    path("agents/bank/transcribe/", transcription_views.transcribe_audio, name="transcribe_audio"),
    path("agents/fraud/", agent_views.fraud_agent_chat, name="fraud_agent_chat"),
    path("transactions/add/", views.add_transaction, name="add_transaction"),
]
