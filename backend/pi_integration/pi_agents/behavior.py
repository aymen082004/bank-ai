import json
from typing import Dict, Any
from .tools import get_user_transactions, analyze_financial_behavior
from .agent_factory import create_structured_agent_executor, BEHAVIOR_SYSTEM_PROMPT

# Create LangChain agent executor (lazy initialization)
_behavior_executor = None

def get_behavior_executor():
    """Lazy initialization of the behavior agent executor."""
    global _behavior_executor
    if _behavior_executor is None:
        from .tools import get_user_transactions, query_neo4j_graph
        tools = [get_user_transactions, query_neo4j_graph]
        _behavior_executor = create_structured_agent_executor(
            tools=tools,
            system_prompt=BEHAVIOR_SYSTEM_PROMPT,
            max_iterations=5,
            verbose=False
        )
    return _behavior_executor


def behavior_agent(state):
    """
    Analyse le comportement financier et la personnalité de l'utilisateur à l'aide d'un agent LangChain avec GraphRAG.
    """
    user_id = state.get("user_id", "default_user")
    
    executor = get_behavior_executor()
    
    # Préparer l'entrée pour l'agent LangChain
    agent_input = f"""
ID Utilisateur: {user_id}

Effectuez une analyse GraphRAG pour extraire la personnalité financière de l'utilisateur:
1. Appelez get_user_transactions avec user_id="{user_id}"
2. Appelez query_neo4j_graph avec user_id="{user_id}" pour obtenir les schémas de transaction et les intérêts précédents
3. Synthétisez les données des deux outils pour déterminer le profil (persona) (Spender/Keeper/Investor/Balanced)
4. Identifiez le pouvoir d'achat et fournissez un insight comportemental basé sur les schémas graphiques.

Retournez le résultat au format JSON.
"""
    
    # Invoquer l'agent LangChain
    result = executor.invoke({"input": agent_input})
    agent_output = result.get("output", "")
    
    # Essayer de parser le JSON de la sortie de l'agent
    analysis = {}
    try:
        start = agent_output.find("{")
        end = agent_output.rfind("}") + 1
        if start != -1 and end > start:
            analysis = json.loads(agent_output[start:end])
    except Exception as e:
        print(f"DEBUG: Échec du parsing de la sortie de l'agent de comportement: {e}")
        analysis = {"persona": "neutre", "purchasing_power": "milieu de gamme", "insight": "Aucune donnée disponible."}
    
    # Mettre à jour l'état avec les résultats de l'analyse
    state["persona"] = analysis.get("persona", "neutre")
    state["purchasing_power"] = analysis.get("purchasing_power", "milieu de gamme")
    state["behavior_insight"] = analysis.get("insight", "")
    
    return state
