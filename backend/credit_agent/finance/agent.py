import sys
import os
import json
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from state import AgentState
from llm_config import llm
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage
from finance.tools import (
    calculate_credit_habitat,
    calculate_credit_consommation,
    calculate_credit_amenagement,
    calculate_credit_auto,
    submit_finance_report
)

# SYSTEM_PROMPT = """Tu es un Analyste Financier Senior à la BH Bank. 
# Ton objectif est de fournir une analyse financière professionnelle, structurée et détaillée en français. 

# STRUCTURE DU RAPPORT (STRICTE) :
# 1. [HEADER] Affiche EXACTEMENT le bloc suivant, en remplaçant les valeurs entre crochets par les NOUVEAUX résultats finaux (ou les derniers si échec). Attention aux unités (ans/mois) :
# Le total estimé de votre demande s'élève à [Montant demandé] TND
# Taux d'intérêt : [Taux] %
# Durée de remboursement : [Durée] ans
# Montant autorisé : [Montant accordé] TND
# Assurances : [Assurance] TND / Mois
# Mensualité : [Mensualité] TND / Mois
# (*) Potentiel Credit : [Montant accordé] TND
# Statut : [SUCCESS ou ÉCHEC_DÉFINITIF]


# 2. [CORPS DU RAPPORT] Rédige 2-3 paragraphes détaillés analysant la situation.
# CRITIQUE : Tu dois OBLIGATOIREMENT commencer par un rappel de la demande initiale (montant et durée de départ choisis par le client) avant d'expliquer le résultat :
#    - Succès Direct : Féliciter le client d'avoir vu sa demande initiale (X sur Y ans) acceptée directement.
#    - Ajustement : Expliquer "La demande initiale de X sur Y ans n'était pas possible (DTI/capacité insuffisante). Après simulation, nous proposons un montant de W sur Z ans".
#    - Échec : Expliquer "Malgré l'allongement de la durée de Y ans à Z ans (le maximum autorisé), la capacité de remboursement reste insuffisante pour accorder le montant demandé de X".

# LOGIQUE CRITIQUE D'ITÉRATION :
# - Si l'outil de calcul (Consommation, Aménagement, Auto) renvoie 'Statut : INSUFFICIENT_CAPACITY', tu DOIS tenter d'augmenter 'duration_choice_years' de +1, **SAUF si tu as déjà atteint la durée maximale autorisée** :
#     * Crédit consommation : 3 ans
#     * Crédit aménagement : 5 ans
#     * Crédit auto : 7 ans (Neuf) / 5 ans (Occasion)
# - CRÉDIT HABITAT : **AUCUNE ITÉRATION N'EST AUTORISÉE.** Le simulateur calcule automatiquement la durée optimale (jusqu'à 25 ans). Tu dois analyser DIRECTEMENT le premier résultat fourni.
# - Si l'outil renvoie 'Statut : ÉCHEC_DÉFINITIF', tu DOIS ARRÊTER immédiatement les calculs et passer à 'submit_finance_report'.
# - Ne jamais dépasser 3 itérations (+1, +1, +1) par rapport à la demande initiale, même si la limite légale n'est pas atteinte.

# CONTRAINTES :
# - Ne JAMAIS répéter la même phrase.
# - Ne PAS lister les données brutes client (revenu, âge, chevaux) sous forme de liste. Utilise une narration fluide.
# - Longueur : 100 à 250 mots.
# - Respecter strictement les limites de durée selon le type de crédit et l'état du véhicule.
# - STOP obligatoire après 'submit_finance_report'.

# 📝 OBJECTIF FINAL :
# - Tu DOIS impérativement appeler 'submit_finance_report' pour soumettre ton rapport final.
# - Produire un rapport clair, fluide, et narratif, mettant en avant les indicateurs financiers clés, l'analyse détaillée et la décision ou recommandation, **sans jamais inventer de données**.
# """
SYSTEM_PROMPT = """
Tu es un Analyste Financier Senior à la BH Bank. 
Ton objectif est de fournir une analyse financière professionnelle, structurée et détaillée en français. 

STRUCTURE DU RAPPORT (STRICTE) :

1. [HEADER] Affiche EXACTEMENT le bloc suivant, en remplaçant les valeurs entre crochets par les résultats finaux (ou les derniers si échec). Attention aux unités (ans/mois) :
Le total estimé de votre demande s'élève à [Montant demandé] TND
Taux d'intérêt : [Taux] %
Durée de remboursement : [Durée] ans
Montant autorisé : [Montant accordé] TND
Assurances : [Assurance] TND / Mois
Mensualité : [Mensualité] TND / Mois
(*) Potentiel Credit : [Montant accordé] TND
Statut : [SUCCESS ou ÉCHEC_DÉFINITIF]

2. [CORPS DU RAPPORT] Rédige 2-3 paragraphes fluides et narratifs analysant la situation :
- Commence OBLIGATOIREMENT par un rappel de la demande initiale (montant et durée choisis par le client).
- Décris la capacité de remboursement, en comparant le montant demandé à la capacité maximale, sans lister les données sous forme de tableau.
- Explique clairement le résultat final :
    * Succès direct : félicite le client pour l’acceptation du montant demandé.
    * Ajustement : explique "La demande initiale de X sur Y ans n'était pas possible (capacité insuffisante). Après simulation, nous proposons un montant de W sur Z ans."
    * Échec : explique "Malgré l’allongement de la durée de Y ans à Z ans (maximum autorisé), la capacité de remboursement reste insuffisante pour accorder le montant demandé de X."

- Mentionne les indicateurs financiers clés de manière narrative, par exemple : mensualité vs revenu, ratio d’endettement, dettes existantes, plafond réglementaire.
- Fournis une conclusion et, si possible, des recommandations concrètes : réduction du montant, prolongation de la durée, ou amélioration de la capacité financière.

LOGIQUE CRITIQUE D'ITÉRATION :
- Si l’outil renvoie 'INSUFFICIENT_CAPACITY', augmente la durée de +1, sauf si la durée maximale autorisée est atteinte :
    * Crédit consommation : 3 ans
    * Crédit aménagement : 5 ans
    * Crédit auto : 7 ans (Neuf) / 5 ans (Occasion)
- Crédit habitat : aucune itération, analyse directement le premier résultat.
- Ne jamais dépasser 3 itérations par rapport à la demande initiale.
- Si l’outil renvoie 'ÉCHEC_DÉFINITIF', arrête immédiatement et appelle 'submit_finance_report'.

CONTRAINTES :
- Ne jamais répéter la même phrase.
- Longueur : 100 à 250 mots.
- STOP obligatoire après 'submit_finance_report'.

OBJECTIF FINAL :
- Appeler impérativement 'submit_finance_report' pour soumettre le rapport.
- Produire un rapport clair, narratif, mettant en avant indicateurs financiers clés, analyse détaillée et décision finale, **sans inventer de données**.
"""

tools = [
    calculate_credit_habitat,
    calculate_credit_consommation,
    calculate_credit_amenagement,
    calculate_credit_auto,
    submit_finance_report
]

# Create the autonomous agent using Langgraph Prebuilt
finance_agent = create_react_agent(llm, tools=tools)

# def run_finance(state: AgentState) -> dict:
#     """
#     Finance Agent node logic for LangGraph.
#     """
#     # If supervisor strictly blocked the execution, early exit
#     if state.get("validation_warnings") and len(state.get("validation_warnings")) > 0:
#         return {"finance_report": "⚠️ Demande de crédit bloquée par le Superviseur. Calculs financiers annulés."}

#     req_details = {
#         "type_credit": state.get("type_credit"),
#         "structured_request": state.get("structured_request", {})
#     }
    
#     human_msg = f"Please process the following request by firing the calculator and analyzing it:\n{json.dumps(req_details, indent=2, ensure_ascii=False)}"
#     print(f"\n[FINANCE AGENT INPUT]\n{human_msg}")
    
#     # Invoke Agent
#     try:
#         response = finance_agent.invoke({
#             "messages": [
#                 SystemMessage(content=SYSTEM_PROMPT),
#                 HumanMessage(content=human_msg)
#             ]
#         })
        
#         # Log basic response metadata
#         print(f"[FINANCE AGENT RESPONSE] Got {len(response['messages'])} messages.")
        
#         # Extract the report from the tool calls inside the AI Messages
#         for msg in reversed(response["messages"]):
#             # Strategy A: Actual Tool Call (Preferred)
#             if hasattr(msg, "tool_calls") and getattr(msg, "tool_calls"):
#                 for tool_call in msg.tool_calls:
#                     if tool_call.get("name") == "submit_finance_report":
#                         args = tool_call.get("args", {})
#                         calc_summary = args.get("calculation_summary_str", "")
#                         fin_analysis = args.get("financial_analysis_str", "")
                        
#                         report_content = fin_analysis
#                         if "Le total estimé" not in fin_analysis and calc_summary:
#                             report_content = f"{calc_summary}\n\n{fin_analysis}"
                            
#                         return {"finance_report": f"### 📊 ANALYSE FINANCIÈRE:\n{report_content}"}
            
#             # Strategy B: Fallback (Text extraction if LLM failed to technically 'call' the tool)
#             if hasattr(msg, "content") and msg.content and getattr(msg, "type", "") == "ai":
#                 content = msg.content.strip()
#                 if "Le total estimé de votre" in content or "Mensualité" in content:
#                     # Clean up the "submit_finance_report" text if it's there
#                     clean_report = content.replace("submit_finance_report", "").replace('{"name": "submit_finance_report"}', '').strip()
#                     return {"finance_report": f"### 📊 ANALYSE FINANCIÈRE:\n{clean_report}"}

#         return {"finance_report": "L'agent financier n'a pas soumis le rapport analytique final."}
#     except Exception as e:
#         return {"finance_report": f"Erreur d'exécution de l'agent financier: {str(e)}"}


def run_finance(state: AgentState) -> dict:
    """
    Finance Agent node logic for LangGraph.
    Stocke uniquement les 7 indicateurs financiers clés dans state.finance_data si succès.
    """
    print(">>> ENTERING FINANCE NODE <<<")
    if state.get("validation_warnings") and len(state.get("validation_warnings")) > 0:
        return {"finance_report": "⚠️ Demande de crédit bloquée par le Superviseur. Calculs financiers annulés."}

    req_details = {
        "type_credit": state.get("type_credit"),
        "structured_request": state.get("structured_request", {})
    }

    human_msg = f"Please process the following request by firing the calculator and analyzing it:\n{json.dumps(req_details, indent=2, ensure_ascii=False)}"
    print(f"\n[FINANCE AGENT INPUT]\n{human_msg}")
    
    try:
        response = finance_agent.invoke({
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=human_msg)
            ]
        })

        report_content = "L'agent financier n'a pas soumis le rapport analytique final."

        # Extraction des indicateurs clés
        def extract_header_values(text: str) -> dict:
            # Patterns plus robustes pour gérer :
            # - Les espaces dans les nombres (1 000.00)
            # - Les virgules vs points
            # - Les unités (TND, DT, dt, tnd)
            # - Le texte narratif pour le RAV
            
            patterns = {
                "loan_amount": r"(?:estimé de votre demande s'élève à|Montant demandé)\s*:\s*([\d\s,.]+)\s*(?:TND|DT)",
                "interest_rate": r"Taux d'intérêt\s*:\s*([\d\s,.]+)\s*%",
                "loan_term": r"Durée de remboursement\s*:\s*([\d\s,.]+)\s*ans",
                "montant_autorise": r"Montant autorisé\s*:\s*([\d\s,.]+)\s*(?:TND|DT)",
                "assurances": r"Assurances\s*:\s*([\d\s,.]+)\s*(?:TND|DT)\s*/\s*Mois",
                "installment": r"Mensualité\s*:\s*([\d\s,.]+)\s*(?:TND|DT)\s*/\s*Mois",
                "potentiel_credit": r"(?:\(\*\)\s*)?Potentiel Credit\s*:\s*([\d\s,.]+)\s*(?:TND|DT)",
                "reste_a_vivre": r"(?:Reste à vivre \(RAV\)|reste à vivre \(RAV\))\s*(?::|de|est de|s'élève à)\s*([\d\s,.]+)\s*(?:TND|DT)",
            }
            
            # Fallback for loan_amount if first one fails
            if "loan_amount" not in text:
                 patterns["loan_amount"] = r"demande\s*s'élève à\s*([\d\s,.]+)\s*(?:TND|DT)"

            result = {}
            for key, pat in patterns.items():
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    try:
                        # Nettoyage du nombre : enlever espaces, remplacer virgule par point
                        raw_val = m.group(1).strip().replace(" ", "").replace(",", ".")
                        val = float(raw_val)
                        if key == "loan_term":
                            # Convert years to months for ML model expected 'loan_term'
                            val = int(val * 12)
                        result[key] = val
                    except:
                        result[key] = m.group(1).strip()
            return result

        # Cherche submit_finance_report dans les tool_calls
        for msg in reversed(response["messages"]):
            if hasattr(msg, "tool_calls") and getattr(msg, "tool_calls"):
                for tool_call in msg.tool_calls:
                    if tool_call.get("name") == "submit_finance_report":
                        args = tool_call.get("args", {})
                        calc_summary = args.get("calculation_summary_str", "")
                        fin_analysis = args.get("financial_analysis_str", "")

                        # On combine tout pour l'extraction et l'affichage
                        full_content = fin_analysis
                        if "Le total estimé" not in fin_analysis and calc_summary:
                            full_content = f"{calc_summary}\n\n{fin_analysis}"
                        
                        out = {"finance_report": f"### 📊 ANALYSE FINANCIÈRE:\n{full_content}"}

                        # Extraction et stockage si SUCCESS
                        # On vérifie dans les deux champs
                        combined_check = (calc_summary + fin_analysis).upper()
                        if "STATUT : SUCCESS" in combined_check:
                            out["finance_data"] = extract_header_values(full_content)
                            # Si l'extraction a échoué à trouver les données vitales, on log un warning
                            if not out["finance_data"]:
                                print("⚠️ WARNING: extraction finance_data a échoué malgré un SUCCESS")

                        return out

            # Fallback texte
            if hasattr(msg, "content") and msg.content and getattr(msg, "type", "") == "ai":
                content = msg.content.strip()
                if "Le total estimé de votre" in content or "Mensualité" in content:
                    report_content = content.replace("submit_finance_report", "").strip()
                    out = {"finance_report": f"### 📊 ANALYSE FINANCIÈRE:\n{report_content}"}
                    if "SUCCESS" in content.upper():
                        out["finance_data"] = extract_header_values(report_content)
                    return out

        return {"finance_report": report_content}

    except Exception as e:
        import traceback
        print(f"Exception in finance node: {e}\n{traceback.format_exc()}")
        return {"finance_report": f"Erreur d'exécution de l'agent financier: {str(e)}"}