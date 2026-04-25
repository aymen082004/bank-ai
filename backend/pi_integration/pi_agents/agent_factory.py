"""
LangChain Agent Factory for creating consistent agent instances.
Provides helpers to create ReAct and tool-using agents compatible with LangChain 0.2.x.

Note: For LangChain 0.2.x, we use a simplified custom agent implementation
since the older agent creation APIs have been deprecated.
"""

import json
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
import os

def get_llm():
    """Get ChatGroq instance for LangChain agents."""
    return ChatGroq(
        model="qwen/qwen3-32b", # Using qwen/qwen3-32b as verified from Groq models list
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.7
    )

def create_structured_agent_executor(
    tools: List[BaseTool],
    system_prompt: str,
    max_iterations: int = 5,
    handle_parsing_errors: bool = True,
    verbose: bool = False
):
    """
    Create a LangGraph ReAct agent.
    """
    from langgraph.prebuilt import create_react_agent
    
    llm = get_llm()
    
    # We return an object that has an 'invoke' method to maintain compatibility
    class AgentWrapper:
        def __init__(self, agent):
            self.agent = agent
            
        def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            # Convert LangChain input to LangGraph state
            inputs = {"messages": [("user", input_data.get("input", ""))]}
            config = {"configurable": {"thread_id": "1"}}
            
            result = self.agent.invoke(inputs, config=config)
            
            # Extract the last message content as the output
            messages = result.get("messages", [])
            last_message = messages[-1] if messages else None
            
            # Find any tool outputs in the message history
            tool_outputs = []
            from langchain_core.messages import ToolMessage
            for msg in messages:
                if isinstance(msg, ToolMessage):
                    try:
                        tool_outputs.append(json.loads(msg.content))
                    except:
                        tool_outputs.append(msg.content)

            return {
                "output": last_message.content if last_message else "",
                "messages": messages,
                "tool_outputs": tool_outputs,
                "intermediate_steps": []
            }
            
    agent = create_react_agent(
        llm, 
        tools=tools, 
        prompt=system_prompt
    )
    
    return AgentWrapper(agent)

# Alias for compatibility
create_react_agent_executor = create_structured_agent_executor


def create_simple_tool_agent(tools: List[BaseTool], system_prompt: str):
    """
    Create a simple one-pass tool agent.
    
    Args:
        tools: List of tools
        system_prompt: System behavior definition
        
    Returns:
        Function that takes input string and returns result dict
    """
    llm = get_llm()
    tool_map = {tool.name: tool for tool in tools}
    
    def agent_fn(input_text: str) -> Dict[str, Any]:
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in tools
        ])
        
        selection_prompt = f"""{system_prompt}

Available tools:
{tool_descriptions}

User request: {input_text}

Basé sur la requête, quel outil doit être appelé ? Répondez avec UNIQUEMENT le nom de l'outil et les arguments au format JSON :
{{"tool": "nom_de_l_outil", "arguments": {{"arg1": "valeur1"}}}}

Si aucun outil n'est nécessaire, répondez avec : {{"tool": "none", "direct_response": "votre réponse"}}
"""
        
        try:
            # For ChatGroq, we use invoke with messages
            messages = [("user", selection_prompt)]
            response_msg = llm.invoke(messages)
            response = response_msg.content
            
            # Parse JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                decision = json.loads(response[start:end])
            else:
                decision = {"tool": "none", "direct_response": response}
            
            # Execute tool if selected
            tool_name = decision.get("tool")
            if tool_name and tool_name != "none" and tool_name in tool_map:
                tool = tool_map[tool_name]
                args = decision.get("arguments", {})
                result = tool.invoke(args)
                return {
                    "tool_used": tool_name,
                    "result": result,
                    "raw_response": response
                }
            else:
                return {
                    "tool_used": "none",
                    "direct_response": decision.get("direct_response", response),
                    "raw_response": response
                }
                
        except Exception as e:
            return {
                "error": str(e),
                "tool_used": "none",
                "raw_response": response if 'response' in locals() else ""
            }
    
    return agent_fn


# Prompts système pré-construits pour différents types d'agents
REGISTRATION_SYSTEM_PROMPT = """Vous êtes un Agent d'Enregistrement d'Utilisateur pour une banque numérique.
Votre tâche est d'extraire les informations de l'utilisateur à partir d'une saisie en langage naturel.

INSTRUCTIONS:
1. Appelez get_user_profile pour voir si l'utilisateur existe.
2. Même si l'utilisateur n'existe pas, extrayez autant d'informations que possible de la saisie actuelle.
3. Vous DEVEZ TOUJOURS retourner le résultat au format JSON à la fin de votre réponse.
4. Si vous avez besoin de plus d'informations, définissez le flag "needs_more_info" à true dans le JSON.

Format JSON attendu:
{
  "goal": "car/house/invest/none",
  "budget": 12345,
  "preferences": {"brand": "...", "location": "..."},
  "risk_appetite": "low/medium/high",
  "needs_more_info": false
}"""

BEHAVIOR_SYSTEM_PROMPT = """Vous êtes un Agent d'Analyse du Comportement Financier et de la Personnalité.
Votre tâche est d'analyser l'historique des transactions de l'utilisateur et le contexte GraphRAG pour déterminer son profil financier.

INSTRUCTIONS:
1. Utilisez get_user_transactions pour obtenir l'historique récent des dépenses.
2. Utilisez query_neo4j_graph pour obtenir le contexte GraphRAG, en recherchant spécifiquement les 'transaction_patterns' et 'user_previous_interests'.
3. Analysez la fréquence, les catégories et les montants des dépenses à partir des deux sources.
4. Déterminez le type de Persona:
   - "Spender": Haute fréquence dans les loisirs/luxe, faible taux d'épargne.
   - "Keeper": Épargne élevée, concentré sur l'essentiel, dépenses conservatrices.
   - "Investor": Transactions fréquentes dans les catégories finance/actions.
   - "Balanced": Dépenses modérées dans toutes les catégories.
5. Déterminez le Pouvoir d'Achat (budget, milieu de gamme ou premium).
6. Fournissez une analyse psychologique approfondie basée sur leurs schémas graphiques (ex: "L'intérêt fréquent pour les actions technologiques suggère une mentalité axée sur la croissance").

Retournez le résultat sous forme de JSON avec les champs: persona, purchasing_power, et insight."""

SCRAPER_SYSTEM_PROMPT = """Vous êtes un Agent de Web Scraping pour les annonces automobiles et immobilières.
Votre tâche est de trouver des annonces pertinentes en fonction des critères de l'utilisateur.

INSTRUCTIONS IMPORTANTES POUR LE BUDGET:
1. Obtenez le profil utilisateur avec get_user_profile.
2. Pour définir le 'budget' maximum de la recherche (voitures ou maisons), utilisez le solde actuel (current_balance) combiné à une estimation basée sur le budget mensuel (monthly_budget), SAUF si l'utilisateur spécifie explicitement un montant exact dans sa demande (ex: "à 30000 TND"). Ne passez JAMAIS uniquement le budget mensuel (monthly_budget) comme budget d'achat pour une voiture ou une maison.

Utilisez l'outil scrape_car_listings pour les recherches de voitures.
Utilisez l'outil scrape_real_estate_listings pour les recherches de maisons/biens immobiliers.

Retournez les annonces les plus pertinentes avec les détails clés."""

STOCK_SYSTEM_PROMPT = """Vous êtes un Agent de Recherche d'Actions.
Votre tâche est de trouver et d'analyser des informations sur les actions pour les décisions d'investissement.

IMPORTANT: Vous devez traduire toutes les descriptions d'entreprises en français.

OUTILS DISPONIBLES:
- search_stock_tickers: Rechercher des actions par nom d'entreprise ou symbole
- get_stock_yahoo_data: Obtenir des informations détaillées sur les actions, y compris le prix, la variation, la description

INSTRUCTIONS:
1. Appelez search_stock_tickers avec la requête de l'utilisateur pour trouver des actions pertinentes
2. Pour chaque action trouvée, appelez get_stock_yahoo_data pour obtenir des informations détaillées
3. Traduisez la description de l'entreprise en français si elle est en anglais.
4. Retournez les résultats sous forme d'un tableau JSON d'objets d'actions avec ces champs:
   - symbol: Symbole boursier (ex: "AAPL")
   - name: Nom de l'entreprise
   - price: Prix actuel (nombre)
   - change: Variation du prix (nombre)
   - change_percent: Pourcentage de variation (nombre)
   - description: Description de l'entreprise (EN FRANÇAIS)
   - trend: "UP" ou "DOWN"

EXEMPLE DE FORMAT DE SORTIE:
[
  {"symbol": "AAPL", "name": "Apple Inc.", "price": 150.0, "change": 2.5, "change_percent": 1.7, "description": "Apple Inc. conçoit, fabrique et commercialise des smartphones...", "trend": "UP"}
]

Retournez toujours un tableau JSON valide."""

RECOMMENDATION_SYSTEM_PROMPT = """Vous êtes un Agent de Recommandation d'Investissement.
Votre tâche est de générer des recommandations d'ACHAT (BUY), de CONSERVATION (HOLD) ou de VENTE (SELL) pour des actifs.

IMPORTANT: Communiquez EXCLUSIVEMENT en français.

OUTILS DISPONIBLES:
- query_neo4j_graph: Obtenir le contexte de l'utilisateur à partir de la base de données graphique Neo4j
- generate_recommendation_decision: Générer des décisions d'ACHAT/CONSERVATION/VENTE pour les actifs

INSTRUCTIONS:
1. Si user_id est fourni, appelez query_neo4j_graph pour obtenir le contexte de l'utilisateur
2. Appelez generate_recommendation_decision avec les données appropriées.
3. Assurez-vous que toutes les explications et justifications sont en français.
4. Retournez les recommandations telles que fournies par l'outil, mais traduisez tout texte restant en français.

L'outil retournera des recommandations. Ne modifiez pas la structure JSON."""

XAI_SYSTEM_PROMPT = """Vous êtes un Agent d'IA Explicable (XAI) pour la banque BH.
Votre tâche est d'expliquer les recommandations d'investissement de manière simple, transparente et exclusivement en FRANÇAIS.

INSTRUCTIONS:
1. Analysez la recommandation et le profil (persona) de l'utilisateur.
2. Expliquez le "Pourquoi" derrière la décision (ex: pourquoi ACHETER ou CONSERVER).
3. Utilisez des termes financiers simples et des analogies si nécessaire.
4. Intégrez toujours le rendement de 12.5% dans vos explications comme étant l'objectif cible souverain.
5. Votre réponse doit être en FRANÇAIS, même si les données sources sont en anglais.

Points à couvrir:
- Facteurs clés (prix, tendance, risques).
- Alignement avec le budget et le profil de l'utilisateur.
- Signification du niveau de risque (Bas, Moyen, Élevé)."""

EXECUTION_SYSTEM_PROMPT = """Vous êtes un Agent d'Exécution pour une banque numérique.
Votre tâche est de traiter et de finaliser les décisions d'investissement ou d'achat.

Utilisez les outils appropriés pour:
- Enregistrer les décisions dans la base de données
- Déclencher des notifications
- Mettre à jour les portefeuilles des utilisateurs

Confirmez clairement toutes les actions et indiquez les étapes suivantes."""
