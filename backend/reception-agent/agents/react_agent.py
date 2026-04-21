from __future__ import annotations
import json
import os
import sys
import re
import time
import httpx
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, List, Dict, Optional
from dotenv import load_dotenv
from langchain_ollama import ChatOllama

# Add necessary paths
current_dir = Path(__file__).resolve().parent
agent_root = current_dir.parent
# Add current directory and dependencies to sys.path
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
if str(agent_root) not in sys.path:
    sys.path.insert(0, str(agent_root))
if str(agent_root / "db") not in sys.path:
    sys.path.insert(0, str(agent_root / "db"))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from bank_tools import AVAILABLE_BANK_TOOLS
from agent_storage import save_action_event, save_chat_event, build_memory_context

# Token Factory Configuration for XAI Audit
TOKEN_FACTORY_URL = "https://tokenfactory.esprit.tn/api/chat/completions"
TOKEN_FACTORY_KEY = os.environ.get("TOKEN_FACTORY_KEY", "sk-1afd8f9c21e049499e6faa1df6faab45")

# Load environment
dotenv_path = Path(__file__).resolve().parents[1] / ".env"
if not dotenv_path.exists():
    dotenv_path = Path(__file__).resolve().parents[2] / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()

# Configuration
LLM_BASE_URL = os.environ.get("FASTFIN_LLM_BASE_URL", "http://localhost:1234/v1")
LLM_MODEL = os.environ.get("FASTFIN_LLM_MODEL", "fastllmm")
LLM_API_KEY = os.environ.get("FASTFIN_LLM_API_KEY", "lm-studio")

SYSTEM_PROMPT = """Tu es l'assistant expert de la BH Bank Tunisie.
Tu dois toujours justifier ta démarche de réflexion.

FORMAT DE RÉPONSE :
Thought: [Ta réflexion logique en français. Explique POURQUOI tu choisis cette action ou cette réponse.]
Action: [Si besoin d'un outil]
Final Answer: [Ta réponse finale au client]

RÈGLES :
1. Ton 'Thought' doit être une justification pour le client (ex: "J'interroge la base car...").
2. Réponds en français professionnel.
3. Anti-hallucination: Utilise uniquement les données retournées par les outils.
4. HISTORIQUE : Sers-toi de l'historique récent pour comprendre le contexte.
"""

async def run_judge_audit(question: str, final_answer: str) -> dict:
    """Audit métrique de la réponse par le LLM Juge de Token Factory."""
    prompt = f"""Tu es l'Auditeur Senior de la BH Bank Tunisie. 
Évalue la fidélité de la RÉPONSE par rapport à la QUESTION.

QUESTION : {question}
RÉPONSE : {final_answer}

RÉPONDS UNIQUEMENT AU FORMAT JSON SUIVANT :
{{
  "fidelity": score_0_100,
  "relevance": score_0_100,
  "verdict": "Fidèle" ou "Halluciné" ou "Partiel",
  "reasoning": "Analyse rapide en 2 phrases"
}}"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                TOKEN_FACTORY_URL,
                headers={"Authorization": f"Bearer {TOKEN_FACTORY_KEY}"},
                json={
                    "model": "hosted_vllm/Llama-3.1-70B-Instruct",
                    "messages": [
                        {"role": "system", "content": "Tu es un auditeur JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0
                }
            )
            resp.raise_for_status()
            res_data = resp.json()
            raw_content = res_data["choices"][0]["message"]["content"].strip()
            json_str = re.sub(r"```json|```", "", raw_content).strip()
            return json.loads(json_str)
    except Exception as e:
        return {"fidelity": 50, "verdict": "Erreur Audit", "reasoning": str(e)}

class BankReactAgent:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.max_steps = 5

    async def run(self, user_question: str) -> dict:
        print(f"[DEBUG BANK] ReAct Cycle: {user_question}")
        memory_context = build_memory_context("action", limit=5)
        
        active_system = SYSTEM_PROMPT
        if memory_context:
            active_system += f"\n\nCONTEXTE MÉMOIRE :\n{memory_context}"

        messages: List[Any] = [
            SystemMessage(content=active_system),
            HumanMessage(content=user_question),
        ]

        rationale_steps = []
        final_answer = ""

        # llm = ChatOpenAI(
        #     model=LLM_MODEL,
        #     base_url=LLM_BASE_URL,
        #     api_key=LLM_API_KEY,
        #     temperature=0,
        # )

        llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "qwen3.5:4b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.2,
            max_tokens=1024,
        )

        
        # BIND TOOLS HERE - Use list of tools directly
        llm_with_tools = llm.bind_tools(AVAILABLE_BANK_TOOLS)

        for step in range(self.max_steps):
            try:
                response = await llm_with_tools.ainvoke(messages)
            except Exception as e:
                print(f"[ERROR] LLM Invoke error: {e}")
                final_answer = f"Erreur de communication avec le modèle: {str(e)}"
                break
            
            content = response.content or ""
            thought_match = re.search(r"(?i)Thought:\s*(.*?)(?=\nAction:|\nFinal Answer:|$)", content, flags=re.DOTALL)
            if thought_match:
                rationale_steps.append(thought_match.group(1).strip())
            
            messages.append(response)

            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    tool_to_call = next((t for t in AVAILABLE_BANK_TOOLS if t.name == tool_name), None)
                    if tool_to_call:
                        observation = await tool_to_call.ainvoke(tool_args)
                        messages.append(ToolMessage(
                            tool_call_id=tool_call["id"],
                            content=str(observation)
                        ))
                        save_action_event({
                            "ts": time.time(),
                            "question": user_question,
                            "tool": tool_name,
                            "result": str(observation)[:500]
                        })
            else:
                final_answer = content
                final_answer = re.sub(r"(?i)Thought:.*?(?=\nFinal Answer:|$)", "", final_answer, flags=re.DOTALL)
                final_answer = re.sub(r"(?i)Final Answer:\s*", "", final_answer).strip()
                break

        if not final_answer:
            final_answer = "Désolé, je n'ai pas pu aboutir à une réponse."

        audit_report = await run_judge_audit(user_question, final_answer)
        xai_dashboard = {
            "strategy": rationale_steps if rationale_steps else ["Analyse directe."],
            "audit": audit_report,
        }

        save_chat_event({
            "ts": time.time(),
            "question": user_question,
            "answer": final_answer,
            "rationale": json.dumps(xai_dashboard, ensure_ascii=False)
        })

        return {
            "answer": final_answer,
            "rationale": json.dumps(xai_dashboard, ensure_ascii=False)
        }

def run_react_agent(user_input: str, **kwargs) -> dict:
    agent = BankReactAgent()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # Use a future or thread to run in existing loop if needed, 
        # but for Django runserver threads, asyncio.run is usually safest.
        return asyncio.run(agent.run(user_input))
    else:
        return loop.run_until_complete(agent.run(user_input))
