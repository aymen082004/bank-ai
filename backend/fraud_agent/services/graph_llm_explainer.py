from services.enhanced_llm_service import llm


def generate_graph_llm_explanation(graph_data):
    """
    Converts graph signals into fraud behavioral intelligence using LLM
    """

    # -------------------------
    # SAFE FORMATTING (IMPORTANT FIX)
    # -------------------------
    if isinstance(graph_data, dict):
        formatted_data = "\n".join(
            f"- {k}: {v}" for k, v in graph_data.items()
        )
    else:
        formatted_data = str(graph_data)

    # -------------------------
    # PROMPT (IMPROVED)
    # -------------------------
    prompt = f"""Signaux du Graphe :
{formatted_data}

RÈGLES STRICTES :
- Pas de markdown (**, -, #, etc.)
- Pas de répétition de "Signaux" ou "Décision"
- Texte simple, 3 phrases maximum
- Décrivez uniquement les patterns de comportement suspects

Fournissez 3 phrases maximum décrivant les patterns comportementaux."""

    return llm(prompt)