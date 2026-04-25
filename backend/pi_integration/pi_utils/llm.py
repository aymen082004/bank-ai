import os
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path
from dotenv import load_dotenv

dotenv_path = Path(__file__).resolve().parents[1] / ".env"
if not dotenv_path.exists():
    dotenv_path = Path(__file__).resolve().parents[2] / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def call_llm(messages, model="qwen/qwen3-32b", max_retries=3):
    """Appel à l'API LLM avec gestion des erreurs et tentatives de secours."""
    import time
    
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
            )
            return completion.choices[0].message.content
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                # Wait before retrying on rate limit
                time.sleep(2)
                continue
            print(f"Erreur d'appel LLM : {e}")
            return "Désolé, je rencontre une difficulté technique pour générer une réponse. Veuillez réessayer dans quelques instants."
    
    return "Service temporairement indisponible."
