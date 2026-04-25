import json
from typing import Dict, Any
from ..pi_utils.llm import call_llm

# LangChain imports
from .agent_factory import create_structured_agent_executor, XAI_SYSTEM_PROMPT

# Lazy initialization
_xai_executor = None

def get_xai_executor():
    """Lazy initialization of the XAI agent executor."""
    global _xai_executor
    if _xai_executor is None:
        # XAI agent doesn't need tools - just generates explanations
        _xai_executor = create_structured_agent_executor(
            tools=[],  # No tools needed for explanation
            system_prompt=XAI_SYSTEM_PROMPT,
            max_iterations=3,
            verbose=False
        )
    return _xai_executor


def xai_agent(state):
    """
    Explique les décisions (XAI) pour l'utilisateur.
    CRITIQUE : Restez sur le sujet - expliquez uniquement ce que l'utilisateur a demandé !
    """
    recommendations = state.get("recommendations", [])
    persona = state.get("persona", "neutral")
    profile = state.get("profile", {})
    goal = profile.get("goal", "").lower()
    listings = state.get("listings", [])
    
    # Déterminer la contrainte de sujet basée sur l'objectif de l'utilisateur
    if "car" in goal:
        topic_constraint = """
        CRITIQUE : L'utilisateur a posé des questions sur les VOITURES. 
        - Expliquez UNIQUEMENT les recommandations de voitures
        - NE mentionnez PAS d'actions, d'obligations, d'ETF ou de fonds d'investissement
        - NE parlez PAS du S&P 500, des obligations d'État ou des ETF technologiques
        - Restez concentré uniquement sur les véhicules et les achats de voitures
        """
        default_msg = "J'ai trouvé quelques voitures pour vous ! Voici les recommandations basées sur votre budget et vos préférences."
    elif "house" in goal or "home" in goal or "apartment" in goal or "maison" in goal:
        topic_constraint = """
        CRITIQUE : L'utilisateur a posé des questions sur les MAISONS/PROPRIÉTÉS.
        - Expliquez UNIQUEMENT les recommandations immobilières
        - NE mentionnez PAS d'actions, d'obligations, d'ETF ou de fonds d'investissement
        - Restez concentré uniquement sur l'immobilier
        """
        default_msg = "J'ai trouvé quelques propriétés pour vous ! Voici les recommandations basées sur votre budget et vos préférences."
    elif "invest" in goal or "stock" in goal or "action" in goal:
        topic_constraint = """
        CRITIQUE : L'utilisateur a posé des questions sur les INVESTISSEMENTS/ACTIONS.
        - Expliquez UNIQUEMENT les recommandations d'investissement
        - NE mentionnez PAS de voitures ou de propriétés
        - Restez concentré uniquement sur les titres et les investissements
        """
        default_msg = "Voici mes recommandations d'investissement basées sur votre profil de risque et vos objectifs."
    else:
        topic_constraint = "Expliquez les recommandations en fonction de ce qui a été demandé."
        default_msg = "Voici mes recommandations pour vous."
    
    if not recommendations:
        if "car" in goal and not listings:
            state["explanation"] = "Je n'ai trouvé aucune voiture correspondant à vos critères dans votre budget. Essayez d'ajuster votre budget ou de rechercher d'autres marques. Vous pouvez également consulter directement automobile.tn pour plus d'options."
        elif "house" in goal and not listings:
            state["explanation"] = "Je n'ai trouvé aucune propriété correspondant à vos critères dans votre budget. Essayez d'ajuster votre budget ou vos critères de recherche."
        else:
            state["explanation"] = default_msg
        return state

    prompt = f"""
    Expliquez ces recommandations à l'utilisateur de manière conviviale et humaine.
    RÉPONDEZ EXCLUSIVEMENT EN FRANÇAIS. C'EST UNE CONSIGNE CRITIQUE.
    Même si les noms d'actifs sont en anglais (ex: Apple), toute l'explication doit être en français.
    
    {topic_constraint}
    
    Profil Utilisateur : {persona}
    Objectif Utilisateur : {goal}
    Recommandations à expliquer : {json.dumps(recommendations, indent=2)}
    
    Règles IMPORTANTES :
    - Langue : FRANÇAIS UNIQUEMENT pour toute la réponse.
    - Si vous utilisez une section de réflexion/thinking, elle doit être en FRANÇAIS aussi.
    - Utilisez "🤔 Réflexion:" au lieu de "Thinking:" ou "<think>".
    - Restez strictement sur le SUJET - discutez uniquement de ce que l'utilisateur a demandé.
    - Expliquez POURQUOI chaque recommandation correspond à son profil ({persona}).
    - Si vous expliquez des voitures : parlez de la valeur, de la fiabilité, de l'adéquation au budget.
    - Si vous expliquez des investissements : parlez du risque, des rendements, de la diversification.
    """
    
    messages = [{"role": "user", "content": prompt}]
    explanation = call_llm(messages)
    
    # Post-traitement : si l'explication mentionne un mauvais sujet, fournir un repli sûr
    explanation_lower = explanation.lower()
    if "car" in goal and any(word in explanation_lower for word in ["bond", "etf", "stock", "s&p", "obligations", "bourse"]):
        # Le LLM est sorti du sujet, utiliser le repli
        explanation = default_msg + "\n\n"
        for rec in recommendations:
            asset = rec.get("asset", "")
            decision = rec.get("decision", "")
            reason = rec.get("reason", "")
            explanation += f"\n**{asset}** - {decision}\n{reason}\n"
    
    state["explanation"] = explanation
    return state
