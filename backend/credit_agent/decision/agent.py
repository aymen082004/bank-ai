import sys
import os
import json
from typing import Literal
from pydantic import BaseModel, Field

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import AgentState
from llm_config import report_llm
from langchain_core.messages import SystemMessage, HumanMessage

class DecisionOutput(BaseModel):
    decision: Literal["APPROUVÉ", "REJETÉ", "REVUE_MANUELLE"] = Field(
        ..., description="La décision finale concernant la demande de crédit."
    )
    explanation: str = Field(
        ..., description="Le rapport détaillé et l'explication professionnelle de la décision finale."
    )

# SYSTEM_PROMPT = """
# Tu es le Comité de Crédit (Decision Agent) de la BH Bank.
# Ton rôle est de prendre la décision finale sur une demande de crédit en te basant sur trois rapports préalables :
# 1. Le rapport du Superviseur (identité, revenus, conformité globale)
# 2. L'analyse Financière (simulation, mathématiques du crédit, capacité de remboursement)
# 3. L'analyse de Risques (modèle ML, probabilité de défaut)

# Instructions :
# - Tu dois lire attentivement ces rapports.
# - Si une des étapes a généré un rejet fort (ex: capacité insuffisante, durée dépassée, ou refus de conformité), la décision DOIT être REJETÉ.
# - Si le risque ML est très élevé (Probabilité > 0.4 ou Grade F/G) avec une capacité serrée, la décision PEUT être REVUE_MANUELLE ou REJETÉ.
# - Si tous les voyants sont au vert (Succès financier, risque faible/modéré, infos valides), la décision DOIT être APPROUVÉ.
# - Tu dois générer une explication narrative détaillée  qui synthétise les points forts et faibles du dossier issus des trois agents, et justifie catégoriquement la décision finale.
# - Rédige de façon prof
SYSTEM_PROMPT = """
Tu es le Comité de Crédit (Decision Agent) de la BH Bank.
Ton rôle est de produire la décision finale sur une demande de crédit, en te basant sur trois types de rapports.

1. Rapport du Superviseur : identité, cohérence des documents, vérification de revenus, dettes.
2. Analyse Financière : (SI DISPONIBLE) simulation complète, DTI, capacité, mensualités.
3. Analyse de Risques : (SI DISPONIBLE) score ML, probabilité de défaut.

---

Instructions détaillées pour générer le rapport final :

⚠️ **ADAPTATION DYNAMIQUE OBLIGATOIRE** ⚠️
Si un rapport (Finance ou Risque) est indiqué "Non fourni", tu NE DOIS PAS l'inventer ni utiliser des variables X/YZ. Tu DOIS SOIT omettre la section, SOIT indiquer : "Analyse non applicable (Dossier rejeté par l'étape précédente)."

Structure type de ton rapport (à adapter selon les données reçues) :

1️⃣ **Résumé initial du dossier**
- Présenter le client et la demande initiale.

2️⃣ **Analyse financière détaillée** *(SEULEMENT SI FOURNIE)*
- Expliquer les calculs clés : Mensualité calculée, Capacité réelle, Ratio DTI, Reste à vivre.
- Comparer la demande initiale vs le montant accordé.

3️⃣ **Analyse du risque** *(SEULEMENT SI FOURNIE)*
- Indiquer : probabilité de défaut, grade, et facteurs d'influence.

4️⃣ **Décision finale du comité**
- **REJETÉ** : Incohérences d'identité, DTI trop élevé, refus superviseur, défaut ML.
- **REVUE_MANUELLE** : risque ML élevé mais capacité limite.
- **APPROUVÉ** : succès sur toute la ligne.
- Fournir la justification claire de cette décision.

5️⃣ **Recommandations** *(SEULEMENT SI PERTINENT)*
- Recommander la nouvelle option du conseiller financier si différente de la demande initiale.
- Si le dossier a été refusé par le superviseur pour faux documents ou identité invalide, indiquer "Aucune recommandation possible, dossier non conforme."

---

✅ **Règles de rédaction**
- Narratif fluide et hyper-professionnel.
- Ne JAMAIS INVENTER de données financières, de scores ou de grades si le texte indique "Non fourni".

⚠️ **FORMAT DE RÉPONSE STRICTEMENT OBLIGATOIRE** ⚠️
Tu DOIS IMPÉRATIVEMENT retourner ta réponse sous forme de dictionnaire ou d'objet validant exactement DEUX clés :
1. `decision` : (EXACTEMENT "APPROUVÉ", "REJETÉ" ou "REVUE_MANUELLE")
2. `explanation` : (Une chaîne contenant ton rapport formaté proprement).
"""

def run_decision(state: AgentState) -> dict:
    print(">>> ENTERING DECISION NODE <<<")
    
    client_info = state.get("client_info", "Non fourni.")
    finance_rep = state.get("finance_report", "Non fourni (Arrêté par le superviseur).")
    risk_rep = state.get("risk_report", "Non fourni (Arrêté par le superviseur).")
    warnings = state.get("validation_warnings")

    # If the workflow was blocked early by the supervisor, inject the exact reasons.
    early_rejection_notice = ""
    if warnings and len(warnings) > 0:
        early_rejection_notice = (
            "\n\n🚨 ATTENTION: LE DOSSIER A ÉTÉ REJETÉ PRÉCIPITAMMENT PAR LE SUPERVISEUR ! 🚨\n"
            "Le pipeline s'est arrêté avant l'analyse financière et risque pour les raisons suivantes :\n"
            f"{ chr(10).join(warnings) }\n"
            "Tu DOIS statuer sur la décision 'REJETÉ' et l'expliquer formellement en basant tout ton texte sur cette interdiction du superviseur."
        )

    human_msg = f"""
Voici les rapports consolidés pour la demande de crédit :

=== 1. RAPPORT SUPERVISEUR ===
{client_info}{early_rejection_notice}

=== 2. ANALYSE FINANCIÈRE ===
{finance_rep}

=== 3. ANALYSE DE RISQUES (ML) ===
{risk_rep}

Sur la base de ces informations, fournis ta décision et ton explication détaillée.
"""

    structured_llm = report_llm.with_structured_output(DecisionOutput)
    
    try:
        print(">>> INVOKING DECISION LLM (WAITING FOR RESPONSE) <<<")
        result: DecisionOutput = structured_llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_msg)
        ])
        print(f">>> DECISION LLM RESPONSE RECEIVED: {result.decision} <<<")
        
        # Formatting the output into a nice markdown block
        icon = "✅" if result.decision == "APPROUVÉ" else "❌" if result.decision == "REJETÉ" else "⚠️"
        
        formatted_decision = f"### {icon} DÉCISION DU COMITÉ : {result.decision}\n\n"
        formatted_decision += f"**Justification détaillée :**\n{result.explanation}"
        
        return {"final_decision": formatted_decision}
        
    except Exception as e:
        import traceback
        print(f">>> EXCEPTION IN DECISION NODE: {e}\n{traceback.format_exc()}")
        return {"final_decision": f"### ⚠️ ERREUR DÉCISION\nImpossible de générer la décision finale: {str(e)}"}
