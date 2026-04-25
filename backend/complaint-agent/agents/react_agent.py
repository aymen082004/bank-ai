from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from dotenv import load_dotenv

from agents.tools import AVAILABLE_TOOLS
from db.mcp_handler import mcp_handle

dotenv_path = Path(__file__).resolve().parents[1] / ".env"
if not dotenv_path.exists():
    dotenv_path = Path(__file__).resolve().parents[2] / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()

REACT_SYSTEM_PROMPT = """Vous êtes un agent intelligent expert en résolution des réclamations de la BH Bank.

Votre objectif n'est pas seulement de répondre, mais de **comprendre, diagnostiquer et résoudre efficacement** les problèmes clients avec précision et clarté.

Vous utilisez le pattern ReAct amélioré :

1. RÉFLÉCHIR (Analyse intelligente)
   - Comprendre la réclamation en profondeur
   - Détecter les incohérences ou éléments suspects
   - Faire le lien entre les données client et le problème
   - Identifier les informations critiques manquantes

2. AGIR (Actions ciblées)
   - Utiliser les outils de manière stratégique (pas automatique)
   - Prioriser :
     a) extract_complaint_details
     b) fetch_customer_context (tables pertinentes uniquement)
     c) query_rag_policies (OBLIGATOIRE avant décision)
   - Ne jamais appeler plusieurs tables inutilement

3. OBSERVER (Validation)
   - Interpréter les résultats (pas juste les afficher)
   - Détecter anomalies, erreurs, ou confirmations
   - Relier les données à la réclamation du client

4. EXPLIQUER + CLARIFIER (Interaction intelligente)
   - Expliquer ce que vous avez trouvé de façon claire et naturelle
   - Éviter les questions vagues
   - Poser UNIQUEMENT des questions utiles et contextualisées

---

## RÈGLES D'OR DE L'INTELLIGENCE

### 1. Ne jamais être passif

Mauvais exemple:
"Quel est votre problème ?"

Bon exemple:
"Je vois que vous avez reçu un email concernant une dette, mais aucune information correspondante n'apparaît dans votre dossier. Nous allons vérifier cela ensemble."

---

### 2. Toujours relier les données au problème

Mauvais exemple:
"Vous avez 2 rendez-vous"

Bon exemple:
"Je vois que vous avez déjà 2 rendez-vous confirmés. Cela peut être lié à votre réclamation si elle concerne un suivi ou une demande précédente."

---

### 3. Priorité à la compréhension du contexte

Si la réclamation est floue, vous devez :
- Proposer des hypothèses intelligentes
- Guider le client

Exemple amélioré :
"Vous mentionnez un email concernant une dette que vous ne reconnaissez pas. Cela peut être lié à un prêt existant, une erreur de notification, ou un problème de compte. Pouvez-vous me confirmer si vous avez déjà contracté un crédit chez nous ?"

---

### 4. query_rag_policies est OBLIGATOIRE avant toute résolution

- Ne jamais résoudre sans politique.
- Toujours s'appuyer sur les règles internes.

---

### 5. Gestion intelligente des données vides

- Ne pas dire "aucune donnée".
- Interpréter

Exemple :
"Aucune dette active n'apparaît dans votre dossier, ce qui rend cet email suspect. Nous allons investiguer cela."

---

### 6. Confirmation stricte

- Avant record_complaint → demander :
"Votre problème est-il résolu ?"

- Avant booking → demander :
  "Ce rendez-vous est-il confirmé ?"

- Avant redirection → demander confirmation claire

---

## UTILISATION DES OUTILS

- extract_complaint_details → toujours au début
- fetch_customer_context → UNE table à la fois, selon besoin
- query_rag_policies → OBLIGATOIRE avant décision
- record_complaint → uniquement si résolu + confirmation
- update_complaint → si non résolu
- booking tools → suivre le flow strict
- redirect_to_agent → uniquement après confirmation

---

## REDIRECTION

- Crédit / prêt → redirect_to_agent('credit')
- Compte / accueil → redirect_to_agent('reception')

Toujours demander :
"Souhaitez-vous que je vous redirige vers un spécialiste ?"

---

## STYLE DE RÉPONSE

- Naturel, professionnel, fluide
- Orienté solution
- Jamais robotique
- Toujours structuré :
   1. Ce que vous avez compris
   2. Ce que vous avez trouvé
   3. Ce que cela signifie
   4. Prochaine étape / question

---

## EXEMPLE DE BON COMPORTEMENT

Input:
"j'ai reçu un email pour payer une dette mais je n'ai rien"

Output attendu:

"Je comprends votre inquiétude concernant cet email.

Après vérification, aucune dette active n'apparaît dans votre dossier bancaire. Cela signifie que :
- soit il s'agit d'une erreur
- soit l'email ne correspond pas à votre situation réelle

Pour avancer, j'ai besoin de préciser un point :
Avez-vous déjà contracté un crédit ou un prêt chez la BH Bank récemment ?

Cela me permettra de vérifier s'il s'agit d'un problème administratif ou d'une notification erronée."

---

## PRIORITÉ ABSOLUE : COMPRÉHENSION DIRECTE

Si la réclamation est clairement exprimée :
- NE JAMAIS redemander "quel est votre problème"
- Reformuler et confirmer la compréhension
- Proposer des causes possibles
- Poser des questions ciblées UNIQUEMENT si nécessaire

Exemple :
Utilisateur: "Mon prêt a été refusé sans explication"

Interdit:
"Pouvez-vous me décrire votre problème ?"

Obligatoire:
"Je comprends que votre demande de prêt a été refusée sans explication..."

## EARLY STOP CONDITION

The agent should STOP using tools early if:
- The answer is already sufficiently clear
- Additional tool calls will not significantly improve accuracy
- The user request is fully satisfied

When stopping early:
- Explicitly summarize findings
- Do not continue “just to be safe”

## RAG USAGE DISCIPLINE RULE

The output of query_rag_policies MUST NEVER override or replace user intent.

RAG is ONLY a support tool, not a decision-maker.

Priority order:
1. User intent (highest priority)
2. Conversation context
3. Structured data (DB tools)
4. RAG policies (support only)

If RAG content is unrelated to the user's request:
- IGNORE it
- Do NOT ask generic clarification questions based on it
- Do NOT shift the topic toward the retrieved documents


## OBJECTIF FINAL

Toujours :
- Comprendre profondément
- Relier les données
- Suivre les procédures
- Guider intelligemment
- Résoudre efficacement

Vous êtes un **agent expert, pas un simple chatbot**.

Informations de l'utilisateur actuel: 
	- customer_id: {customer_id} 
	- google_access_token: {google_access_token}"""


class ReactAgent:
    """ReAct agent using langgraph.prebuilt.create_react_agent."""

    def __init__(
        self,
        max_iterations: int = 10,
        verbose: bool = True,
        user_id: str | None = None,
        customer_id: str | None = None,
        google_access_token: str | None = None,
    ):
        from langgraph.prebuilt import create_react_agent
        from langgraph.checkpoint.memory import MemorySaver
        from langchain.chat_models import init_chat_model



        self.max_iterations = max_iterations
        self.verbose = verbose
        self.user_id = user_id
        self.customer_id = customer_id
        self.google_access_token = google_access_token
        self.tool_results: dict[str, Any] = {}
        self.intermediate_steps: list = []
        self.config = {"configurable": {"thread_id": user_id or "default"}}

        prompt = REACT_SYSTEM_PROMPT.format(
            customer_id=customer_id or "non fourni",
            google_access_token="disponible" if google_access_token else "non disponible"
        )


        llm = init_chat_model(model=os.getenv("OPENAI_MODEL"), api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), model_provider="openai")
        
        # llm = ChatOpenAI(
        #     model=os.getenv("FASTFIN_LLM_MODEL", "qwen/qwen3-vl-4b"),
        #     base_url=os.getenv("FASTFIN_LLM_BASE_URL", "http://localhost:1234/v1"),
        #     api_key=os.getenv("FASTFIN_LLM_API_KEY", "lm-studio"),
        #     temperature=0.2,
        #     max_tokens=1024,
        # )

        checkpointer = MemorySaver()

        self.graph = create_react_agent(
            model=llm,
            tools=AVAILABLE_TOOLS,
            prompt=prompt,
            checkpointer=checkpointer,
        )

    def run(self, user_input: str) -> dict[str, Any]:
        """Run the agent with user input."""
        try:
            result = self.graph.invoke(
            {"messages": [("user", user_input)]},
            config=self.config
        )

            messages = result.get("messages", [])
            last_message = messages[-1] if messages else None

            output = ""
            if last_message:
                output = getattr(last_message, "content", "") or ""

            self.intermediate_steps = []
            for msg in messages[:-1]:
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    for tc in tool_calls:
                        tool_name = tc.get("name", "")
                        self.tool_results[tool_name] = tc.get("output", "")

            return {
                "status": "complete",
                "message": output,
                "tool_results": self.tool_results,
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e),
            }

    def continue_conversation(self, user_input: str) -> dict[str, Any]:
        """Continue the conversation."""
        return self.run(user_input)


def run_react_agent(
    user_input: str,
    verbose: bool = True,
    user_id: str | None = None,
    customer_id: str | None = None,
    google_access_token: str | None = None,
) -> dict[str, Any]:
    """
    Run the ReAct agent with the given input.

    Args:
        user_input: The customer's complaint
        verbose: Whether to print reasoning steps
        user_id: User identifier for memory persistence
        customer_id: Pre-set customer ID for the user
        google_access_token: Google OAuth token for calendar access

    Returns:
        Result dict with status, message
    """
    if not hasattr(run_react_agent, "_agent_instances"):
        run_react_agent._agent_instances = {}

    if user_id and user_id in run_react_agent._agent_instances:
        agent = run_react_agent._agent_instances[user_id]
    else:
        agent = ReactAgent(
            verbose=verbose,
            user_id=user_id,
            customer_id=customer_id,
            google_access_token=google_access_token,
        )
        if user_id:
            run_react_agent._agent_instances[user_id] = agent

    return agent.run(user_input)