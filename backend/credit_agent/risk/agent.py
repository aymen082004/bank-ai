import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import AgentState
from llm_config import llm
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from risk.tools import (
    get_customer,
    predict_risk,
    submit_risk_report
)

# ==============================
# SYSTEM PROMPT
# ==============================
SYSTEM_PROMPT = """
Tu es un Risk Analyst Senior à la BH Bank. Ton rôle est d'évaluer le risque de défaut d'un client de manière autonome en utilisant tes outils.

OBJECTIF ET PIPELINE STRICT (Ordre OBLIGATOIRE) :

1. APPELER l'outil `get_customer(numero_compte)`
   → Tu obtiendras `personal_info`, `employment`, et `credit_profile`.

2. DÉTERMINER le `grade_subgrade` dynamiquement :
   → Utilise `credit_score` et d'autres indicateurs.
   → Mapping indicatif pour le Grade (Lettre) :
       A: 720+ | B: 680-719 | C: 640-679 | D: 600-639 | E: 580-599 | F: 550-579 | G: < 550
   → Détermine le Subgrade (1 à 5, 1 étant le meilleur) en fonction du `debt_to_income_ratio` (DTI) ou d'autres facteurs de risque.
   → Exemple: B3, D5, A1.

3. APPELER l'outil `predict_risk(input_data_json)`
   → Tu dois construire un STRING JSON contenant UNE SEULE liste par variable, combinant les infos DB et les `finance_data` fournis.
   → Variables obligatoires dans le JSON (remplace avec les valeurs réelles):
     {
        "age": [age],
        "annual_income": [annual_income],
        "monthly_income": [monthly_income],
        "debt_to_income_ratio": [debt_to_income_ratio],
        "credit_score": [credit_score],
        "num_of_open_accounts": [num_of_open_accounts],
        "total_credit_limit": [total_credit_limit],
        "current_balance": [current_balance],
        "loan_amount": [loan_amount], 
        "interest_rate": [interest_rate],
        "loan_term": [loan_term],
        "installment": [installment],
        "num_of_delinquencies": [num_of_delinquencies],
        "gender": ["Male/Female"],
        "marital_status": ["Married/Single/etc"],
        "education_level": ["Bachelor/etc"],
        "employment_status": ["Employed/etc"],
        "loan_purpose": ["type_credit"],
        "grade_subgrade": ["Ton grade calculé, ex: B3"]
     }
   → Exécuter l'outil avec ce JSON exact. Il te retournera `default_probability`, `risk_level`, et `top_features`.

4. APPELER l'outil `submit_risk_report` (Dernière étape)
   → Produis un rapport narratif (2-3 paragraphes, 100 à 250 mots).
   → [HEADER] EXACTEMENT :
     Account id : [ID depuis base de données]
     Montant demandé : [loan_amount] TND
     Durée : [loan_term] mois
     Type de crédit : [loan_purpose]
     Probabilité de défaut : [default_probability]
     Niveau de risque : [risk_level]
   → [CORPS DU RAPPORT] Ton analyse narrative DOIT synthétiser ces 3 sources :
     1. Le profil client (personal_info, employment, credit_profile issus de get_customer)
     2. Les paramètres financiers de la demande (finance_data initiaux)
     3. Les résultats ML (probabilité, risk_level et top_features issus de predict_risk)
   → Explique les facteurs principaux et décris les points forts/faibles du dossier.
   → Conclus par une recommandation finale (ex: "Risque faible, prêt envisageable").
   → Ne liste pas les variables sous forme de tableau.

CONTRAINTES :
- Ne jamais inventer de données.
- Ne pas répéter les phrases.
- STOP obligatoire après `submit_risk_report`.
"""

tools = [
    get_customer,
    predict_risk,
    submit_risk_report
]

risk_agent = create_react_agent(llm, tools=tools)


# ==============================
# RUN FUNCTION
# ==============================
def run_risk(state: AgentState) -> dict:
    """
    Risk Agent node
    """
    print(">>> ENTERING RISK NODE <<<")
    numero_compte = state.get("customer_id")
    finance_data = state.get("finance_data", {})
    type_credit = state.get("type_credit", "")
    amount = state.get("amount", 0.0)
    repayment_period = state.get("repayment_period", 0)

    # Sécurité
    if not numero_compte or not finance_data:
        return {
            "risk_report": "⚠️ Données client ou simulation financière manquantes."
        }

    # Le dictionnaire `finance_data` est explicitement donné à l'agent
    loan_info = {
        "loan_amount": finance_data.get("loan_amount", amount),
        "interest_rate": finance_data.get("interest_rate", 7.0),
        "loan_term": finance_data.get("loan_term", repayment_period * 12),
        "installment": finance_data.get("installment", 0.0),
        "type_credit": type_credit
    }

    req = {
        "numero_compte": numero_compte,
        "finance_data": loan_info
    }

    human_msg = (
        "Analyse le risque de ce client. Voici son 'numero_compte' et les 'finance_data' de la demande de crédit.\n"
        "Exécute ton PIPELINE dans l'ordre strict : get_customer -> calcule grade_subgrade -> predict_risk -> submit_risk_report.\n"
        f"INPUT =\n{json.dumps(req, indent=2, ensure_ascii=False)}"
    )

    try:
        response = risk_agent.invoke({
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=human_msg)
            ]
        })

        # EXTRACTION TOOL RESULT
        for msg in reversed(response["messages"]):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if tool_call.get("name") == "submit_risk_report":
                        args = tool_call.get("args", {})
                        return {
                            "risk_report": args.get("risk_analysis", ""),
                        }

        # Fallback (si tool pas appelé correctement)
        for msg in reversed(response["messages"]):
            if hasattr(msg, "content") and msg.content:
                return {"risk_report": msg.content}

        return {"risk_report": "⚠️ Aucun rapport de risque généré."}

    except Exception as e:
        import traceback
        return {
            "risk_report": f"Erreur Risk Agent : {str(e)}\n\n{traceback.format_exc()}"
        }