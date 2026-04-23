import json
from typing import Dict, Any
from .tools import get_user_profile, query_neo4j_graph
from .agent_factory import create_structured_agent_executor, REGISTRATION_SYSTEM_PROMPT

# Create LangChain agent executor (lazy initialization)
_registration_executor = None

def get_registration_executor():
    """Lazy initialization of the registration agent executor."""
    global _registration_executor
    if _registration_executor is None:
        tools = [get_user_profile, query_neo4j_graph]
        _registration_executor = create_structured_agent_executor(
            tools=tools,
            system_prompt=REGISTRATION_SYSTEM_PROMPT,
            max_iterations=5,
            verbose=False
        )
    return _registration_executor


def registration_agent(state):
    """
    Extrait le profil structuré à partir de la saisie utilisateur à l'aide de l'agent LangChain.
    Gère le dialecte tunisien (Derja), le français et l'anglais.
    """
    user_id = state.get("user_id", "default_user")
    user_input = state.get("user_input", "")
    
    executor = get_registration_executor()
    
    # Préparer l'entrée pour l'agent LangChain
    agent_input = f"""
ID Utilisateur: {user_id}
Saisie Utilisateur: "{user_input}"

Extrayez le profil de l'utilisateur comprenant:
1. budget (en TND) - utilisez la valeur de la base de données si non spécifiée. Convertissez les termes tunisiens comme "melyoun" (30 melyoun = 30000) et les termes français comme "mille" (50 mille = 50000).
2. goal (car/house/invest)
3. risk_appetite (low/medium/high)
4. preferences (marque, emplacement, etc.)

Appelez get_user_profile avec user_id="{user_id}" pour obtenir les données existantes.
Retournez le profil extrait au format JSON.
"""
    
    # Invoquer l'agent LangChain
    result = executor.invoke({"input": agent_input})
    agent_output = result.get("output", "")
    
    # Essayer de parser le JSON de la sortie de l'agent
    profile = {}
    try:
        start = agent_output.find("{")
        end = agent_output.rfind("}") + 1
        if start != -1 and end > start:
            profile = json.loads(agent_output[start:end])
        else:
            # Parsing de secours si le JSON n'est pas parfaitement formaté
            input_lower = user_input.lower()
            if any(kw in input_lower for kw in ["car", "voiture", "auto", "كرهبة"]):
                profile["goal"] = "car"
            elif any(kw in input_lower for kw in ["house", "maison", "dar", "appartement", "villa"]):
                profile["goal"] = "house"
            elif any(kw in input_lower for kw in ["invest", "stock", "bourse", "action"]):
                profile["goal"] = "invest"
    except Exception as e:
        print(f"DEBUG: Échec du parsing de la sortie de l'agent d'enregistrement: {e}")
        # Fallback minimal
        input_lower = user_input.lower()
        if "voiture" in input_lower or "car" in input_lower: profile["goal"] = "car"
        elif "maison" in input_lower or "house" in input_lower: profile["goal"] = "house"
    
    state["profile"] = profile
    print(f"DEBUG: Profil Final: {profile}")
    return state
