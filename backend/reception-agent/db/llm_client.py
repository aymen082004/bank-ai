import os
import requests
import re

LLM_MODEL = os.environ.get("FASTFIN_LLM_MODEL", "nvidia/nemotron-3-nano-4b")

def _build_chat_url(base: str) -> str:
    """
    Supporte:
    - base = http://127.0.0.1:1234        -> /v1/chat/completions
    - base = http://127.0.0.1:1234/v1     -> /chat/completions
    - base = http://127.0.0.1:1234/v1/    -> /chat/completions
    """
    base = (base or "").rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"

def _atomic_clean(text: str) -> str:
    """Nettoyage intelligent des balises et artefacts LLM (V4 - Anti-monologue)."""
    if not text: return ""
    
    # 1. Extraction via balises <REP> (Priorité absolue)
    match = re.search(r"<REP>(.*?)</REP>", text, re.DOTALL | re.IGNORECASE)
    if match:
        tag_ans = match.group(1).strip()
        if len(tag_ans) >= 1: return tag_ans

    # 2. Enlever la réflexion balisée (DeepSeek/Nemotron)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()

    # 3. Anti-monologue : Si le modèle continue de penser sans balises ("Wait, ...", "Hmm, ...", "Let me...")
    # On cherche un marqueur de fin de réflexion : une ligne qui commence avec les mots finaux courants
    final_answer_markers = [
        r"^(so\s+the\s+answer|so\s+the\s+response|so\s+response|so:|réponse\s*:|voici|votre\s+solde|votre\s+compte|bonjour|le\s+solde|désolé|félicitations|votre\s+demande|nous\s+avons|le\s+compte|l'opération|un\s+probl|malheureusement)",
    ]
    lines = text.split("\n")
    final_start = -1
    for i, line in enumerate(lines):
        s = line.strip().lower()
        if any(re.match(m, s, re.IGNORECASE) for m in final_answer_markers):
            final_start = i
            break
    if final_start > 0:
        text = "\n".join(lines[final_start:])

    # 4. Filtrage par lignes : supprimer les préambules de monologue interne
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    forbidden_prefixes = (
        "okay", "let's", "let me", "the user", "source", "i will", "wait,", "hmm,", "hmm.",
        "d'après", "voyons", "en me", "je vais", "here is", "firstly", "specifically",
        "basé sur", "actually,", "so,", "now,", "looking", "the problem", "the result",
        "the data", "the first", "the second", "so the", "so maybe", "maybe", "probably",
        "in french", "in banking", "so response", "so answer", "thus produce", "now produce",
        "let's do that", "car ce type de message", "but that's for", "possibly later",
        "first,", "the first source", "the question is", "but the user", "according to rule",
        "the sources", "the wikipedia", "since the sources", "if there's no", "but wait",
        "alternatively,", "so maybe the", "the second source", "contexte:", "context:",
        "source:", "source locale", "source web", "faiss:", "web:"
    )
    
    clean_lines = []
    for line in lines:
        l_low = line.lower()
        is_forbidden = any(l_low.startswith(f) for f in forbidden_prefixes)
        is_short_meta = len(line) < 15 and (line.endswith(":") or line.endswith("?"))
        if not is_forbidden and not is_short_meta:
            clean_lines.append(line)

    if clean_lines:
        result = "\n".join(clean_lines)
        result = re.sub(r"(?im)^\s*(source|contexte|context)\s*:.*$", "", result).strip()
        result = re.sub(r"</?REP>", "", result, flags=re.IGNORECASE).strip()
        return result or "INFORMATION_NON_TROUVEE"

    text = re.sub(r"</?REP>", "", text, flags=re.IGNORECASE).strip()
    return text or "INFORMATION_NON_TROUVEE"

def ask_llm(system_prompt: str, user_content: str, temperature: float = 0.0, clean: bool = True, max_tokens: int = 1024) -> str:
    """Fonction de base pour interroger le LLM de manière robuste."""
    base = os.environ.get("FASTFIN_LLM_BASE_URL", "http://127.0.0.1:1234")
    url = _build_chat_url(base)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
    try:
        resp = requests.post(url, json={
            "model": LLM_MODEL, 
            "messages": messages, 
            "temperature": temperature,
            "max_tokens": max_tokens
        }, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if "choices" in data:
            content = data["choices"][0]["message"].get("content", "")
            if not clean:
                return content
            return _atomic_clean(content)
    except Exception as e:
        print(f"[LLM_CLIENT] Erreur: {e}")
    return ""
