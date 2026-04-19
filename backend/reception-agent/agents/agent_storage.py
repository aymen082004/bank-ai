from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

_lock = threading.Lock()

# On place les fichiers dans le dossier de l'agent pour éviter de polluer la racine
BASE_DIR = Path(__file__).resolve().parent
CHAT_HISTORY_FILE = str(BASE_DIR / "chat_history.jsonl")
ACTION_HISTORY_FILE = str(BASE_DIR / "agent_history.jsonl")


def save_agent_event(event: Dict[str, Any], file_path: str | None = None) -> None:
    """
    Enregistre un event en format JSONL (une ligne par action).
    """
    if file_path is None:
        file_path = ACTION_HISTORY_FILE

    line = json.dumps(event, ensure_ascii=False)
    with _lock:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def _resolve_path(file_path: str | None, default_path: str) -> str:
    if file_path:
        return file_path
    return default_path


def save_chat_event(event: Dict[str, Any], file_path: str | None = None) -> None:
    save_agent_event(event, file_path=_resolve_path(file_path, CHAT_HISTORY_FILE))


def clear_memory(agent_kind: str, file_path: str | None = None) -> None:
    kind = (agent_kind or "").lower().strip()
    path = _resolve_path(file_path, CHAT_HISTORY_FILE if kind == "chat" else ACTION_HISTORY_FILE)
    with _lock:
        try:
            if os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    pass
        except Exception:
            pass


def save_new_session(agent_kind: str, file_path: str | None = None) -> None:
    """Insère un marqueur de nouvelle session."""
    kind = (agent_kind or "").lower().strip()
    path = _resolve_path(file_path, CHAT_HISTORY_FILE if kind == "chat" else ACTION_HISTORY_FILE)
    with _lock:
        line = json.dumps({"is_new_session": True, "ts": time.time()}, ensure_ascii=False)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def save_action_event(event: Dict[str, Any], file_path: str | None = None) -> None:
    save_agent_event(event, file_path=_resolve_path(file_path, ACTION_HISTORY_FILE))


def load_recent_events(limit: int = 50, file_path: str | None = None, default_path: str = ACTION_HISTORY_FILE) -> List[Dict[str, Any]]:
    path = _resolve_path(file_path, default_path)
    if not os.path.exists(path):
        return []

    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
        except Exception:
            return []

    selected = lines[-max(1, int(limit)):]
    events: List[Dict[str, Any]] = []
    for line in selected:
        try:
            events.append(json.loads(line))
        except Exception:
            continue
    return events


def _fmt_short(value: Any, max_len: int = 180) -> str:
    txt = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    txt = (txt or "").replace("\n", " ").strip()
    if len(txt) <= max_len:
        return txt
    return txt[:max_len] + "..."


def build_memory_context(agent_kind: str, limit: int = 8) -> str:
    """
    Génère un contexte texte court à injecter dans le prompt LLM.
    """
    kind = (agent_kind or "").lower().strip()
    default_path = CHAT_HISTORY_FILE if kind == "chat" else ACTION_HISTORY_FILE
    events = load_recent_events(limit=50, default_path=default_path)
    if not events:
        return ""

    # Ne garder que la session actuelle
    session_events = []
    for ev in reversed(events):
        if ev.get("is_new_session"):
            break
        session_events.append(ev)
    
    session_events.reverse()
    session_events = session_events[-limit:]

    if not session_events:
        return ""

    lines = ["Mémoire récente:"]
    for ev in session_events:
        q = _fmt_short(ev.get("question", ""))
        a = _fmt_short(ev.get("answer", ""))
        if kind == "chat":
            lines.append(f"- Q: {q} | R: {a}")
        else:
            tool = _fmt_short(ev.get("tool", "none"))
            res = _fmt_short(ev.get("result", ""))
            lines.append(f"- Q: {q} | Tool: {tool} | Résultat: {res} | Réponse: {a}")
    return "\n".join(lines)
