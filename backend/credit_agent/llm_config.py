import os
from dotenv import load_dotenv

load_dotenv(override=True)
from langchain_openai import ChatOpenAI
from typing import Optional

# --- Agent d'exécution (outils) ---
# Configuration via variables d'environnement (optionnel)
# --- Smart Base URL selection (Docker vs. Host) ---
_is_docker = os.environ.get("IS_DOCKER", "0") == "1"
_default_base = "http://host.docker.internal:1234/v1" if _is_docker else "http://localhost:1234/v1"

# Explicitly handle empty or unset env vars
_llm_base = os.environ.get("FASTFIN_LLM_BASE_URL", "").strip()
if not _llm_base:
    _llm_base = _default_base

_llm_key = os.environ.get("FASTFIN_LLM_API_KEY", "lm-studio").strip()
_llm_model = os.environ.get("FASTFIN_LLM_MODEL", "qwen/qwen3-vl-4b").strip()

# --- Logging for Debugging ---
print(f"\n[LLM CONFIG] IS_DOCKER: {_is_docker}")
print(f"[LLM CONFIG] Base URL:  {_llm_base}")
print(f"[LLM CONFIG] Key used:  {'***' if _llm_key else 'None'}")
print(f"[LLM CONFIG] Model:     {_llm_model}\n", flush=True)

llm = ChatOpenAI(
    temperature=float(os.environ.get("FASTFIN_LLM_TEMPERATURE", "0.1")),
    base_url=_llm_base,
    api_key=_llm_key,
    model=_llm_model,
    # max_tokens=int(os.environ.get("FASTFIN_LLM_MAX_TOKENS", "4096")),
)

# --- Agent de Rapport / Décision ---
_report_llm_base = os.environ.get("FASTFIN_REPORT_LLM_BASE_URL", _llm_base)
_report_llm_key = os.environ.get("FASTFIN_REPORT_LLM_API_KEY", _llm_key)
_report_llm_model = os.environ.get("FASTFIN_REPORT_LLM_MODEL", "hosted_vllm/Llama-3.1-70B-Instruct")

report_llm = ChatOpenAI(
    temperature=float(os.environ.get("FASTFIN_REPORT_LLM_TEMPERATURE", "0.5")),
    base_url=_report_llm_base,
    api_key=_report_llm_key,
    model=_report_llm_model,
    # max_tokens=int(os.environ.get("FASTFIN_REPORT_LLM_MAX_TOKENS", "4096")),
)
