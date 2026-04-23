import json
from typing import Dict, Any, List
from ..pi_utils.llm import call_llm
from ..pi_utils.db_neo4j import neo4j_handler
from .car_recommender import car_recommendation_agent, house_recommendation_agent

# LangChain imports
from .tools import query_neo4j_graph, generate_recommendation_decision
from .agent_factory import create_react_agent_executor, RECOMMENDATION_SYSTEM_PROMPT

# Lazy initialization
_recommendation_executor = None

def get_recommendation_executor():
    """Lazy initialization of the recommendation agent executor."""
    global _recommendation_executor
    if _recommendation_executor is None:
        tools = [query_neo4j_graph, generate_recommendation_decision]
        _recommendation_executor = create_react_agent_executor(
            tools=tools,
            system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
            max_iterations=5,
            verbose=False
        )
    return _recommendation_executor


def recommendation_agent(state):
    """
    Génère des décisions d'investissement (ACHAT / CONSERVATION / VENTE) basées sur l'objectif de l'utilisateur.
    Utilise l'agent LangChain ReAct avec le contexte Neo4j et les outils de génération de décision.
    CRITIQUE : Recommandez uniquement le type d'actif demandé par l'utilisateur !
    """
    user_id = state.get("user_id", "default_user")
    profile = state.get("profile", {})
    persona = state.get("persona", "neutre")
    stocks = state.get("stocks", [])
    goal = profile.get("goal", "").lower()
    
    # Déterminer quel type de recommandations fournir
    if any(kw in goal for kw in ["car", "voiture", "auto", "كرهبة"]):
        # Utiliser l'agent de recommandation spécialisé pour les voitures avec web scraping
        return car_recommendation_agent(state)
    elif any(kw in goal for kw in ["house", "home", "apartment", "maison", "dar", "appartement", "propriété", "immobilier"]):
        # Utiliser l'agent de recommandation spécialisé pour les maisons avec web scraping
        return house_recommendation_agent(state)
    
    # Pour les recommandations d'investissement/actions, utiliser l'agent LangChain
    if any(kw in goal for kw in ["invest", "stock", "bourse", "action"]):
        executor = get_recommendation_executor()
        
        # Préparer les actifs pour la recommandation
        assets = stocks if stocks else []
        budget = profile.get("budget", 0)
        if not assets:
            state["recommendations"] = [{
                "asset": "Recherche d'investissement", 
                "decision": "HOLD", 
                "reason": f"Aucune option d'investissement trouvée. Essayez de rechercher des actions spécifiques (ex: 'action Apple', 'Tesla') ou posez des questions sur les opportunités d'investissement dans votre budget de {budget:,} TND."
            }]
            return state
        
        # Appeler l'agent LangChain
        agent_input = f"""
ID Utilisateur: {user_id}
Persona: {persona}
Budget: {profile.get("budget", 0)} TND
Objectif: {goal}

Actifs disponibles ({len(assets)}):
{json.dumps(assets[:5], indent=2)}

Étapes:
1. Appelez query_neo4j_graph avec user_id="{user_id}" pour obtenir le contexte
2. Appelez generate_recommendation_decision avec:
   - asset_type="INVESTMENT"
   - assets=<les actifs disponibles>
   - persona="{persona}"
   - budget={profile.get("budget", 0)}
   - graph_context=<résultat de l'étape 1>

Retournez les recommandations sous forme de liste JSON.
"""
        result = executor.invoke({"input": agent_input})
        agent_output = result.get("output", "")
        tool_outputs = result.get("tool_outputs", [])
        
        # Parser les recommandations de la sortie
        recommendations = []
        
        # Vérifier si l'outil a retourné des recommandations directement
        for output in tool_outputs:
            if isinstance(output, list) and len(output) > 0 and isinstance(output[0], dict) and "asset" in output[0]:
                recommendations = output
                break
        
        # Fallback au parsing de la réponse textuelle de l'agent
        if not recommendations:
            try:
                start = agent_output.find("[")
                end = agent_output.rfind("]") + 1
                if start != -1 and end > start:
                    recommendations = json.loads(agent_output[start:end])
            except Exception as e:
                print(f"DEBUG: Échec du parsing de la sortie de l'agent de recommandation: {e}")
                # Fallback de base
                recommendations = [{"asset": s["symbol"], "decision": "HOLD", "reason": "Analyse du marché en cours."} for s in assets[:2]]
            
        state["recommendations"] = recommendations
        return state
    
    return state
