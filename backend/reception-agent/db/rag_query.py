from __future__ import annotations

import os
import json
import asyncio
import httpx
import time
import re
from typing import Any, Dict, List, Optional

# Configuration
LLM_BASE_URL = os.environ.get("FASTFIN_LLM_BASE_URL", "http://127.0.0.1:1234/v1")
LLM_MODEL = os.environ.get("FASTFIN_LLM_MODEL", "qwen/qwen3-vl-4b")

SYSTEM_PROMPT = """Tu es l'expert en recherche de la BH Bank Tunisie.

RÈGLES CRITIQUES DE RAISONNEMENT :
1. CHERCHE DANS FAISS D'ABORD : Tu dois toujours chercher tes informations avec l'outil 'search_faiss' en premier. Si tu trouves l'information, réponds.
2. SI NON TROUVÉ -> PASSE AU WEB : Si l'outil 'search_faiss' ne trouve pas l'information ou te signale qu'elle est hors sujet, tu dois DIRECTEMENT passer à l'outil 'search_web' pour chercher sur internet.
3. ANTI-HALLUCINATION : N'invente jamais d'informations. Base-toi uniquement sur les sources.
4. CITATIONS : Utilise toujours [Source X] pour justifier tes affirmations.

FORMAT DE RÉFLEXION :
Avant d'appeler un outil ou de fournir ta réponse, rédige ton raisonnement impérativement entre balises <thought> et </thought>.
La réponse destinée à l'utilisateur doit être rédigée après la balise </thought>. Ne mets pas de libellé "Final Answer:".
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_faiss",
            "description": "Recherche dans la documentation interne de la banque (PDFs, manuels).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "La question ou les mots clés à chercher."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Recherche sur le Web pour des informations externes ou d'actualité.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "La question à poser au Web."}
                },
                "required": ["query"]
            }
        }
    }
]

async def run_judge_audit(question: str, contexts: List[Dict], answer: str) -> Dict:
    """Audit métrique de la réponse par un LLM Juge."""
    if not contexts:
        return {
            "score": 0,
            "fidelity": 0,
            "relevance": 0,
            "verdict": "Aucune source",
            "reasoning": "L'IA a répondu sans aucune base documentaire trouvée."
        }
    
    full_text_context = "\n---\n".join([f"[{c['id']}] Source: {c['source']}\n{c['content']}" for c in contexts])
    
    prompt = f"""Tu es l'Auditeur Senior de la BH Bank Tunisie. 
Évalue la fidélité de la RÉPONSE par rapport aux DOCUMENTS DE RÉFÉRENCE.

DOCUMENTS :
{full_text_context}

QUESTION : {question}
RÉPONSE : {answer}

Tu dois évaluer sur 100 :
1. FIDÉLITÉ (Fidelity) : Est-ce que chaque affirmation est dans les documents ? (0 si hallucination)
2. PERTINENCE (Relevance) : Est-ce que ça répond bien à la question ?

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
                "https://tokenfactory.esprit.tn/api/chat/completions",
                headers={"Authorization": "Bearer sk-1afd8f9c21e049499e6faa1df6faab45"},
                json={
                    "model": "hosted_vllm/Llama-3.1-70B-Instruct",
                    "messages": [{"role": "system", "content": "Tu es un auditeur JSON."}, {"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 512
                }
            )
            resp.raise_for_status()
            res_data = resp.json()
            raw_content = res_data["choices"][0]["message"]["content"].strip()
            # Nettoyage JSON si le LLM ajoute des balises ```json
            json_str = re.sub(r"```json|```", "", raw_content).strip()
            return json.loads(json_str)
    except Exception as e:
        return {"score": 50, "verdict": "Erreur Audit", "reasoning": f"Impossible d'effectuer l'audit : {str(e)}"}

async def ask_chat_agent(query: str, memory_context: str = "") -> Dict[str, Any]:
    try:
        # Prompt enrichi pour les citations
        CUSTOM_SYSTEM = SYSTEM_PROMPT + "\nIMPORTANT : Utilise toujours des citations [Source 1], [Source 2] dans ta réponse pour justifier tes dires."
        
        if memory_context:
            CUSTOM_SYSTEM += f"\n\nHISTORIQUE RÉCENT DE LA CONVERSATION :\n{memory_context}\nATTENTION : Sers-toi de cet historique pour comprendre le sujet actuel. Par exemple, si l'utilisateur dit 'combien coûte ce crédit ?', utilise l'historique pour formuler la requête complète à l'outil (ex: 'coût du crédit automobile') plutôt que de chercher 'ce crédit'."

        messages = [{"role": "system", "content": CUSTOM_SYSTEM}]
        messages.append({"role": "user", "content": query})

        print(f"[DEBUG RAG] Recherche pour: '{query[:50]}'")
        rationale_steps = []
        all_retrieved_sources = []

        for step in range(4):
            async with httpx.AsyncClient(timeout=600.0) as client:
                resp = await client.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    headers={"Authorization": "Bearer lm-studio"},
                    json={
                        "model": LLM_MODEL,
                        "messages": messages,
                        "tools": TOOLS_SCHEMA,
                        "tool_choice": "auto",
                        "temperature": 0,
                        "max_tokens": 1024
                    }
                )
                resp.raise_for_status()
                data = resp.json()
            
            if not data.get("choices"): break

            msg = data["choices"][0]["message"]
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls", [])
            messages.append(msg)  # CRITIQUE: Ajouter la réponse de l'assistant avant d'ajouter le résultat du tool

            # Extraction du Thought
            thought_match = re.search(r"<thought>(.*?)</thought>", content, flags=re.DOTALL | re.IGNORECASE)
            if thought_match:
                rationale_steps.append(thought_match.group(1).strip())

            finish_reason = data["choices"][0].get("finish_reason", "")
            if finish_reason == "stop" or not tool_calls:
                # --- NETTOYAGE RIGOUREUX ---
                final_answer = content
                final_answer = re.sub(r"(?i)<thought>.*?</thought>", "", final_answer, flags=re.DOTALL)
                final_answer = re.sub(r"(?i)Final Answer:\s*", "", final_answer).strip()

                if not final_answer: final_answer = "Désolé, je n'ai pas trouvé d'information."
                
                # --- AUDIT MÉTRIQUE ---
                print("[DEBUG RAG] Audit métrique par le Juge...")
                audit_report = await run_judge_audit(query, all_retrieved_sources, final_answer)
                
                # Format final pour le Dashboard
                xai_dashboard = {
                    "strategy": rationale_steps,
                    "audit": audit_report,
                    "sources": all_retrieved_sources
                }

                return {
                    "answer": final_answer, 
                    "status": "SUCCESS", 
                    "rationale": json.dumps(xai_dashboard) # On envoie le JSON structuré
                }

            for tc in tool_calls:
                name = tc["function"]["name"]
                raw_args = tc["function"].get("arguments", "{}")
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                
                tool_res_str = ""
                if name == "search_faiss":
                    import rag_engine
                    results = rag_engine.retrieve_context(args.get("query", ""))
                    all_retrieved_sources.extend(results)
                    
                    # FILTRE DE PERTINENCE : Si les scores sont mauvais, on incite au Web
                    is_relevant = any(r.get('distance', 1.0) < 0.85 for r in results)
                    if not is_relevant and results:
                        tool_res_str = "[SYSTEM] Alerte : Les documents internes trouvés semblent peu pertinents (scores de distance élevés). Si l'information n'est pas clairement dans ces textes, utilise IMMÉDIATEMENT search_web."
                    
                    tool_res_str += "\n" + "\n".join([f"[{r['id']}] Source: {r['source']}\n{r['content']}" for r in results])
                
                elif name == "search_web":
                    try:
                        from tavily import TavilyClient
                        t_api_key = os.environ.get("TAVILY_API_KEY", "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")
                        if t_api_key:
                            t_client = TavilyClient(api_key=t_api_key)
                            # On ajoute "BH Bank Tunisie" pour préciser la recherche
                            web_resp = t_client.search(query=f"BH Bank Tunisie {args.get('query', '')}", max_results=3)
                            web_results = web_resp.get("results", [])
                            
                            # On vide les sources FAISS (puisqu'elles n'ont pas répondu à la question)
                            all_retrieved_sources.clear()

                            # On convertit les résultats Web en 'sources' pour le dashboard
                            for i, wr in enumerate(web_results):
                                sid = f"Source Web {len(all_retrieved_sources)+1}"
                                all_retrieved_sources.append({
                                    "id": sid,
                                    "content": wr.get("content", ""),
                                    "source": wr.get("url", "Site Web"),
                                    "title": wr.get("title", "")
                                })
                                tool_res_str += f"\n[{sid}] Site: {wr.get('title')} | Lien: {wr.get('url')}\nContenu: {wr.get('content')}\n"
                        else:
                            tool_res_str = "Erreur : TAVILY_API_KEY non configurée."
                    except Exception as e:
                        tool_res_str = f"Erreur Recherche Web : {str(e)}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", "0"),
                    "content": tool_res_str or "Aucun résultat trouvé."
                })

        return {"answer": "Réponse : INFORMATION_NON_TROUVEE", "status": "LIMIT_REACHED"}
    except Exception as e:
        print(f"[ERROR RAG] {e}")
        return {"answer": f"Erreur de recherche: {str(e)}", "status": "ERROR"}