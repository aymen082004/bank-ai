import requests
import random
import json
from typing import Dict, Any, List
from ..pi_utils.stock_api import get_ticker_details, search_tickers, get_snapshot_ticker, get_related_companies
from ..pi_utils.llm import call_llm

# LangChain imports
from .tools import search_stock_tickers, get_stock_yahoo_data
from .agent_factory import create_structured_agent_executor, STOCK_SYSTEM_PROMPT

# Lazy initialization
_stock_executor = None

def get_stock_executor():
    """Lazy initialization of the stock agent executor."""
    global _stock_executor
    if _stock_executor is None:
        tools = [search_stock_tickers, get_stock_yahoo_data]
        _stock_executor = create_structured_agent_executor(
            tools=tools,
            system_prompt=STOCK_SYSTEM_PROMPT,
            max_iterations=5,
            verbose=False
        )
    return _stock_executor


def stock_agent(state):
    """
    Récupère des données boursières détaillées à l'aide de l'agent LangChain avec Yahoo Finance.
    Gère à la fois la recherche et la récupération de tickers spécifiques en fonction de l'intention.
    """
    user_input = state.get("user_input", "")
    
    executor = get_stock_executor()
    
    # Préparer l'entrée pour l'agent LangChain
    agent_input = f"""
Requête utilisateur: "{user_input}"

Analysez si l'utilisateur recherche des actions spécifiques ou demande des options d'investissement générales.

Si recherche spécifique:
- Appelez search_stock_tickers avec query="<nom de l'entreprise ou symbole>"
- Pour chaque résultat, appelez get_stock_yahoo_data avec ticker=<symbole> et data_type="full"

Si demande d'investissement générale:
- Utilisez les tickers par défaut: AAPL, TSLA, MSFT, GOOGL
- Appelez get_stock_yahoo_data pour chacun

Retournez des données boursières complètes, y compris le prix, la variation, la description et les entreprises liées.
Retournez les résultats sous forme de tableau JSON d'objets d'actions.
"""
    
    # Invoquer l'agent LangChain
    result = executor.invoke({"input": agent_input})
    agent_output = result.get("output", "")
    
    # Essayer de parser le JSON de la sortie de l'agent
    stocks_data = []
    try:
        # Rechercher un tableau JSON dans la sortie
        start = agent_output.find("[")
        end = agent_output.rfind("]") + 1
        if start != -1 and end > start:
            stocks_data = json.loads(agent_output[start:end])
    except Exception as e:
        print(f"DEBUG: Échec du parsing de la sortie de l'agent boursier: {e}")
        # Repli final si l'agent échoue complètement
        from ..pi_utils.yahoo_finance import get_stock_info
        default_tickers = ["AAPL", "TSLA", "MSFT", "GOOGL"]
        stocks_data = [get_stock_info(t) for t in default_tickers]
            
    state["stocks"] = stocks_data
    return state
