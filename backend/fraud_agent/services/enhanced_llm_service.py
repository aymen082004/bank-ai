"""
Enhanced LLM Service with Natural Language Understanding
Supports both structured and natural language queries
"""

from openai import OpenAI
import json
import re
import os
from typing import Optional, Dict
import logging
import services.logger

logger = logging.getLogger(__name__)
# =========================
# INIT LLM (OpenRouter)
# =========================
llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"#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
)


# =========================
# LLM CALL HELPER
# =========================
def llm(prompt: str, model: str = "mistralai/ministral-14b-2512", max_tokens: int = 150) -> str:
    """
    Simple LLM wrapper for text generation

    Args:
        prompt: The prompt to send to the LLM
        model: The model to use (default: mistralai/ministral-14b-2512)
        max_tokens: Maximum tokens to generate

    Returns:
        Generated text string
    """
    try:
        response = llm_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"LLM error: {str(e)}"


# =========================
# ENHANCED PARAMETER EXTRACTION
# =========================
def extract_params_enhanced(prompt: str) -> dict:
    """
    Enhanced parameter extraction supporting both:
    1. Structured format: client_id=client181,label=Suspicious
    2. Natural language: "verify fraud for client181 suspicious only"
    """
    
    params = {}
    prompt_lower = prompt.lower()
    
    # Method 1: Try structured format first (key=value)
    pattern = r"(\w+)\s*=\s*['\"]?([\w\.\-]+)['\"]?"
    matches = re.findall(pattern, prompt)
    
    if matches:
        params = {k: v for k, v in matches}
    
    # Method 2: Natural language extraction
    
    # Extract client_id
    # Patterns: "client181", "client 181", "for client181"
    client_patterns = [
        r'client[\s_-]?(\d+)',
        r'client[\s_-]?([a-zA-Z0-9]+)',
        r'for\s+client[\s_-]?([a-zA-Z0-9]+)',
        r'of\s+client[\s_-]?([a-zA-Z0-9]+)'
    ]
    
    for pattern in client_patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            params['client_id'] = f"client{match.group(1)}"
            break
    
    # Extract label
    # Patterns: "suspicious only", "fraud only", "label=Suspicious"
    if 'suspicious' in prompt_lower:
        if 'only' in prompt_lower or 'suspicious' in prompt_lower:
            params['label'] = 'Suspicious'
    
    if 'fraud' in prompt_lower and 'label' not in params:
        if 'only' in prompt_lower or 'fraud' in prompt_lower:
            params['label'] = 'Fraud'
    
    if 'non-fraud' in prompt_lower or 'clean' in prompt_lower or 'normal' in prompt_lower:
        if 'only' in prompt_lower:
            params['label'] = 'Non-Fraud'
    
    # Extract date
    # Patterns: "2021-01-04", "on 2021-01-04", "date 2021-01-04"
    date_pattern = r'(\d{4}[-/]\d{2}[-/]\d{2})'
    date_match = re.search(date_pattern, prompt)
    if date_match:
        params['date'] = date_match.group(1).replace('/', '-')
    
    # Extract year
    # Patterns: "year 2021", "in 2021", "2021"
    year_pattern = r'(?:year|in)\s+(\d{4})|(?:^|\s)(\d{4})(?:\s|$)'
    year_match = re.search(year_pattern, prompt_lower)
    if year_match:
        year = year_match.group(1) or year_match.group(2)
        if year and 2000 <= int(year) <= 2030:
            params['year'] = int(year)
    
    # Extract compte_id
    compte_pattern = r'compte[\s_-]?([a-zA-Z0-9]+)'
    compte_match = re.search(compte_pattern, prompt_lower)
    if compte_match:
        params['compte_id'] = f"compte{compte_match.group(1)}"
    
    # Extract carte_id
    carte_pattern = r'carte[\s_-]?([a-zA-Z0-9]+)|card[\s_-]?([a-zA-Z0-9]+)'
    carte_match = re.search(carte_pattern, prompt_lower)
    if carte_match:
        card_id = carte_match.group(1) or carte_match.group(2)
        params['carte_id'] = f"carte{card_id}"
    
    # Convert types
    for k, v in params.items():
        if isinstance(v, str):
            if v.lower() == "true":
                params[k] = True
            elif v.lower() == "false":
                params[k] = False
            elif v.isdigit():
                params[k] = int(v)
            else:
                try:
                    params[k] = float(v)
                except:
                    pass
    
    return params


# =========================
# GENERATE EXPLANATION
# =========================

def generate_explanation(account_summary: dict, card_summary: dict = None, 
                         explainability_context: str = None) -> dict:
    """
    Generate explanation with explainability integration
    
    Args:
        account_summary: Account risk metrics
        card_summary: Card risk metrics (optional)
        explainability_context: Feature importance and model explanation from ModelExplainer
    
    Returns:
        Dict with decision, reasoning, and LLM explanation
    """

    # =========================
    # 1. DECISION LOGIC (FAST RULES)
    # =========================
    decision = "Non-Fraud"
    reason = "Normal behavior"
    insight = "No anomalies detected"
    action = "No action needed"

    acc_score = account_summary.get("risk_score", 0)
    card_score = card_summary.get("risk_score", 0) if card_summary else 0

    if card_score >= 8:  # Updated threshold for new scale
        decision = "Fraud"
        reason = "Card anomaly detected"
        insight = "Account normal but card shows abnormal behavior"
        action = "Block card immediately"

    elif acc_score + card_score >= 12:  # Updated threshold for new scale
        decision = "Fraud"
        reason = "High combined risk"
        insight = "Multiple anomalies detected"
        action = "Investigate immediately"

    elif acc_score + card_score >= 6:  # Updated threshold for new scale
        decision = "Suspicious"
        reason = "Moderate anomalies"
        insight = "Unusual behavior detected"
        action = "Monitor closely"

    # =========================
    # 2. LLM PROMPT (ENHANCED WITH EXPLAINABILITY)
    # =========================
    
    # Include explainability context if available
    explainability_section = ""
    if explainability_context:
        explainability_section = f"\n\nINSIGHTS DES CARACTÉRISTIQUES :\n{explainability_context}"
    
    prompt = f"""
    Vous êtes un analyste en détection de fraude. Générez une explication concise de pourquoi cette transaction est signalée.

    MÉTRIQUES DE TRANSACTION :
    • Score de risque compte : {acc_score:.2f}/10
    • Score de risque carte : {card_score:.2f}/10
    • Transactions compte : {account_summary.get('total_tx', 0)}
    • Ratio de risque élevé : {account_summary.get('high_risk_ratio', 0):.1%}
    • Score moyen d'anomalie : {account_summary.get('avg_score', 0):.4f}

    DÉCISION : {decision}

    TÂCHE : Expliquez en 2-3 phrases pourquoi c'est {decision.lower()}. Soyez spécifique sur les facteurs contributifs.
    
    RÈGLES ABSOLUES (respecter strictement) :
    1. INTERDIT : Autoencoder, LSTM, modèle, algorithme, IA, machine learning, réseau de neurones, modèles
    2. INTERDIT de répéter la décision dans l'explication
    3. INTERDIT de répéter les scores ou métriques brutes
    4. INTERDIT de markdown (**, ##, -, *, _)
    5. INTERDIT de phrases comme "Décision :" ou "Voici l'explication"
    6. UNIQUEMENT décrire le comportement anormal (montants, fréquence, patterns suspects)
    7. Texte simple comme un agent bancaire, 2-3 phrases maximum
    """

    try:
        response = llm_client.chat.completions.create(
            model="mistralai/ministral-14b-2512",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        llm_text = response.choices[0].message.content.strip()

    except Exception as e:
        llm_text = f"LLM unavailable. Analysis: {decision} with scores Account={acc_score:.2f}, Card={card_score:.2f}"

    # =========================
    # FINAL OUTPUT
    # =========================
    return {
        "decision": decision,
        "reason": reason,
        "insight": insight,
        "action": action,
        "llm_explanation": llm_text,
        "explainability_included": explainability_context is not None
    }


def generate_judge_report(agent_result: Dict) -> Dict:
    """
    Ask an LLM to act as a human judge (senior fraud investigator).
    Takes the full agent result (scores, graph, explainability) and
    returns a concise, actionable report suitable for a bank operator.

    Returns a dict with either parsed JSON fields or the raw LLM text.
    """

    # Safely extract fields
    account = agent_result.get("account", {}) or {}
    card = agent_result.get("card", {}) or {}
    graph = agent_result.get("graph", {}) or {}
    graph_expl = agent_result.get("graph_explanation", "")
    ml_expl = agent_result.get("ml_explainability", {}) or {}
    ml_context = ml_expl.get("llm_context", "") if isinstance(ml_expl, dict) else str(ml_expl)

    # Build evidence block
    metrics_block = {
        "decision": agent_result.get("decision"),
        "auto_confidence": agent_result.get("confidence"),
        "total_risk_score": agent_result.get("total_risk_score"),
        "account": account,
        "card": card,
        "graph_features": graph.get("features", {}),
    }

    prompt = f"""
Vous êtes un enquêteur senior en fraude bancaire. Examinez l'analyse automatisée ci-dessous et produisez un rapport concis et accessible pour un agent des opérations.

DONNÉES D'ENTRÉE (JSON) :
{json.dumps(metrics_block, indent=2)}

APERÇU DU GRAPHE :
{graph_expl}

CONTEXTE D'EXPLICABILITÉ ML :
{ml_context}

RÈGLES ABSOLUES (à respecter strictement) :
1. INTERDIT de mentionner : Autoencoder, LSTM, modèle, algorithme, IA, machine learning, réseau de neurones
2. INTERDIT de répéter la décision dans le résumé
3. INTERDIT de répéter le score de confiance
4. INTERDIT de mentionner "Score total" ou des valeurs numériques de score
5. INTERDIT d'utiliser le markdown (**, ##, -, *, etc.)
6. INTERDIT de dire "Décision de fraude" ou "Décision :" au début
7. Le résumé doit être en langage naturel simple, comme un agent bancaire parle
8. MAXIMUM 2-3 phrases courtes, focus sur le comportement anormal uniquement

TÂCHES :
1) Confirmez ou révisez la décision (Fraude / Suspect / Non-Fraude) - champ final_decision.
2) Fournissez une action recommandée simple - champ recommended_action.
3) Fournissez UNIQUEMENT une description du comportement suspect (montants inhabituels, fréquence anormale) - champ summary. PAS de répétition de la décision ou confiance.

FORMAT DE SORTIE : Retournez UNIQUEMENT un objet JSON avec les clés :
  - final_decision: string
  - final_confidence: number (0-1)
  - recommended_action: string
  - summary: string court (2-3 phrases maximum, sans répéter la décision)
  - evidence: liste de strings (jusqu'à 5, optionnel)
  - raw_llm: (optionnel) texte brut si l'analyse échoue
"""

    judge_model = os.getenv("JUDGE_MODEL", "mistralai/ministral-14b-2512")

    try:
        response = llm_client.chat.completions.create(
            model=judge_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        text = response.choices[0].message.content.strip()
    except Exception as e:
        return {"error": f"Judge LLM call failed: {e}"}

    # Try to extract JSON from the LLM output
    try:
        # Some LLMs wrap JSON in markdown; find first '{'
        start = text.find('{')
        if start != -1:
            json_text = text[start:]
            parsed = json.loads(json_text)
            return parsed
    except Exception:
        # Fall back to returning raw text
        return {"raw_llm": text}

    return {"raw_llm": text}

# =========================
# BACKWARD COMPATIBILITY
# =========================
def extract_params(prompt: str) -> dict:
    """Backward compatible function"""
    return extract_params_enhanced(prompt)


# =========================
# TESTING
# =========================
if __name__ == "__main__":
    test_cases = [
        "verify the fraud for client181 suspicious only",
        "client_id=client181,label=Suspicious",
        "check client 181 for fraud",
        "analyze client181 suspicious transactions only",
        "client181 fraud only",
        "show me client181 data from 2021",
        "client181 suspicious on 2021-01-04"
    ]
    
    logger.info("%s", "="*70)
    logger.info("TESTING ENHANCED PARAMETER EXTRACTION")
    logger.info("%s", "="*70)
    
    for test in test_cases:
        logger.info("Input: %s", test)
        params = extract_params_enhanced(test)
        logger.info("Extracted: %s", params)
