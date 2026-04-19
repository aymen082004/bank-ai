import sys
import os
import json
import re
from typing import Any, Dict, List, Optional, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from state import AgentState
from llm_config import llm
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from supervisor.tools import (
    extract_payslip_data_tool,
    validate_payslip_date,
    validate_customer_identity,
    get_customer,
    compare_salary_ocr_vs_db,
    update_customer_salary,
    update_dti_from_payslip,
    verify_capacity,
    get_bank_params,
    prepare_credit_request,
    submit_supervisor_report,
)

# High-agentic supervisor: the LLM chains tools, reasons, and decides the flow.
# SYSTEM_PROMPT = """
# You are an autonomous Supervisor Agent for BH Bank credit applications.
# You must REASON step by step, CALL TOOLS in a logical order, and finish with exactly ONE call to submit_supervisor_report.

# MANDATORY PIPELINE (follow this order; STOP = do not continue with later steps — go directly to step 9 with rejection details in validation_warnings_json):
# 1. Extract OCR → extract_payslip_data_tool
# 2. Validate payslip → validate_payslip_date
#    → If invalid → STOP → reject
# 3. Fetch customer → get_customer
# 4. Validate identity → validate_customer_identity
#    → If invalid → STOP → reject
# 5. Compare salary → compare_salary_ocr_vs_db
#    → If needs_update = true → update_customer_salary
# 6. Verify capacity → verify_capacity
#    → If negative → STOP → reject
# 7. Get bank params → get_bank_params
# 8. Prepare request → prepare_credit_request
# 9. Final decision → submit_supervisor_report

# STRICT — single source of truth (no invented data):
# - get_customer(numero_compte): use ONLY the string in "numero_compte" from extract_payslip_data_tool output (24 hex characters). Never invent another account id.
# - validate_payslip_date(date_str): use ONLY "date_paiement" from that same extract JSON. Never validate a random or example date.
# - validate_customer_identity: pass the FULL "personal_info" object from get_customer (include nom, prenom, cin, etc.). Do not pass a truncated dict like {age: 23} only.
# - prepare_credit_request: ocr_data_json must be the real extract JSON (at least salary_net, credit_entreprise, nom_prenom, numero_compte, date_paiement). personal_info_json must be ONLY '{"personal_info": {"age": <int>}}' (no full customer document).
# - Do NOT re-call extract_payslip_data_tool or get_customer for the same payslip unless the previous call returned an error or {}. Avoid duplicate contradictory passes.

# Available tools (use them as needed — you are in charge of the sequence):
# - extract_payslip_data_tool(pdf_path)
# - validate_payslip_date(date_str)  → must be "VALIDE" to proceed with a normal dossier
# - get_customer(numero_compte)      → Mongo customer JSON
# - validate_customer_identity(nom_prenom, cin, personal_info dict from DB)
# - compare_salary_ocr_vs_db(ocr_salary_net, db_monthly_income)
#   → ALWAYS call this after get_customer + OCR. It returns JSON with "needs_update": true/false.
#   → Call update_customer_salary ONLY when needs_update is true. If false, skip update.
# - update_customer_salary(customer_id, new_salary, new_annual_income, new_dti)
#   → Only after compare_salary_ocr_vs_db says needs_update true.
# - verify_capacity(salary_net, credit_entreprise, loans_json)
#   → loans_json must be a SMALL JSON string: only the loans array, e.g. json.dumps(customer["loans"]) or "[]".
#   → Do NOT pass the full customer document here.
# - get_bank_params()
# - prepare_credit_request(credit_type, user_input_json, ocr_data_json, personal_info_json, bank_params_json)
#   → personal_info_json: ONLY '{"personal_info": {"age": <number>}}' from get_customer (age field). No other customer fields.
#   → ocr_data_json must be the real extract JSON.
# - submit_supervisor_report(...)  → FINAL step only, once.
#   You MUST invoke this tool with arguments (do not paste the report only as plain text / JSON in the chat — some runtimes require the actual tool call).
#   Note: the backend will set accounts_info_json.solde from DB credit_profile.current_balance and credit_history_str from DB loans; your values may be overwritten for accuracy.

# Critical rules:
# 1) If validate_payslip_date ≠ "VALIDE", explain rejection in validation_warnings_json and still finish with submit_supervisor_report.
# 2) If validate_customer_identity ≠ "VALIDE", same — reject and report.
# 3) If verify_capacity returns exhausted capacity (negative capacity in the message), reject per bank rules and report.
# 4) Prefer short JSON in tool arguments; never paste unnecessary nested blobs.

# Your narrative in client_info_summary should reflect what you actually did (which tools, key numbers).
# """

# SYSTEM_PROMPT = '''You are a Supervisor Agent for BH Bank credit applications.

# Your job:
# - Call tools in the correct order
# - Make a final decision
# - Call submit_supervisor_report EXACTLY ONCE at the end

# ====================
# PIPELINE (STRICT ORDER)
# ====================
# 1. extract_payslip_data_tool(pdf_path)
# 2. validate_payslip_date(date_paiement)
#    → If not "VALIDE" → REJECT → go to final step

# 3. get_customer(numero_compte)
# 4. validate_customer_identity(nom_prenom, cin, personal_info)
#    → If not "VALIDE" → REJECT → go to final step

# 5. compare_salary_ocr_vs_db(ocr_salary_net, db_monthly_income)
#    → If needs_update = true → update_customer_salary

# 6. verify_capacity(salary_net, credit_entreprise, loans_json)
#    → If capacity negative → REJECT → go to final step

# 7. get_bank_params()
# 8. prepare_credit_request(...)
# 9. submit_supervisor_report (FINAL STEP)

# ====================
# DATA RULES
# ====================
# - Always use data from previous tool outputs
# - Never invent values

# - numero_compte → ONLY from OCR
# - date_paiement → ONLY from OCR

# - validate_customer_identity:
#   → use FULL personal_info from get_customer

# - verify_capacity:
#   → pass ONLY loans array (not full customer)

# - prepare_credit_request:
#   → personal_info_json = {"personal_info": {"age": <age>}}
#   → ocr_data_json = OCR output (no changes)

# ====================
# IMPORTANT
# ====================
# - Do NOT call tools twice unnecessarily
# - Use SMALL JSON (no full customer object)
# - Do NOT include file paths in tool arguments
# - Ensure JSON is complete (no truncation)

# ====================
# REJECTION RULES
# ====================
# Reject if:
# - payslip invalid
# - identity invalid
# - capacity negative

# ====================
# FINAL OUTPUT
# ====================
# Call submit_supervisor_report with:
# - decision: APPROVED or REJECTED
# - decision_reason
# - validation_warnings_json
# - client_info_summary (steps + key numbers) '''

SYSTEM_PROMPT = '''Vous êtes un Agent Superviseur pour les demandes de crédit de la BH Bank.

Votre rôle :
- Appeler les outils dans le bon ordre manuellement.
- Suivre les étapes déjà exécutées.
- Prendre une décision finale.
- Appeler submit_supervisor_report EXACTEMENT UNE SEULE FOIS à la fin.

====================
PIPELINE (ORDRE STRICT)
====================
Étape 1 : extract_payslip_data_tool(pdf_path)
Étape 2 : validate_payslip_date(date_paiement)
   → Si ≠ "VALIDE" → REJET → aller directement à submit_supervisor_report

Étape 3 : get_customer(numero_compte)
     → Enregistrer bien les info du client comme ils sont dans la base de données , tu n'est pas autorisé de modifier les info du client surtout cin tu ajouter 1 au niveau
     du 3 eme chiffre a partir de la droite ce n'est pas autorisé de modifier les info du client aussi tu oblie le 3 eme chiffre a partir de la droite du cin le cin
     original est 'cin': '94571014' et tu as mis 'cin': '9457114' ce n'est pas autorisé de modifier les info du client
Étape 4 : validate_customer_identity(nom_prenom, cin, personal_info)
   → Si la sortie n’est pas exactement « VALIDE » (ex. message d’erreur ou « … | … ») → REJET → aller directement à submit_supervisor_report
   → Ne pas enchaîner les étapes 5 à 8 (même logique qu’un rejet à l’étape 2).

Étape 5 : compare_salary_ocr_vs_db(ocr_salary_net, db_monthly_income)
   → Si needs_update = true → update_customer_salary

Étape 6 : update_dti_from_payslip(customer_id, net_salary, old_dti_ratio, new_payslip_charges)
   → OBLIGATOIRE et TOUJOURS exécuté pour mettre à jour le DTI !
   * customer_id = le champ _id retourné par get_customer
   * net_salary = salaire net depuis l'OCR (ex. 1244.97)
   * old_dti_ratio = debt_to_income_ratio actuel (le ratio exact, ex: 0.032) lu depuis la DB via get_customer
   * new_payslip_charges = crédit entreprise ou autres retenues de la fiche de paie.

Étape 7 : verify_capacity(salary_net, credit_entreprise, loans_json)
   → Si la sortie n’est pas exactement « OK » (capacité négative, message d’erreur, etc.) → REJET → aller directement à submit_supervisor_report
   → Ne pas enchaîner les étapes 8 et 9 (même logique qu’un rejet aux étapes 2 ou 4).

Étape 8 : get_bank_params()
Étape 9 : prepare_credit_request(credit_type, amount, repayment_period, user_input_details_json, ocr_data_json, personal_info_json, bank_params_json)
Étape 10 : submit_supervisor_report (ÉTAPE FINALE)

====================
SUIVI D’ÉTAT
====================
- Maintenir une liste `completed_steps`.
- NE JAMAIS répéter une étape déjà réussie.
- Continuer uniquement à partir de la dernière étape complétée.
- Si un outil échoue, NE PAS réessayer. Utiliser les dernières données valides ou rejeter.

====================
RÈGLES DE DONNÉES
====================
- Toujours utiliser les données issues des outils précédents.
- Ne jamais inventer de valeurs.

- numero_compte → UNIQUEMENT depuis l’OCR
- date_paiement → UNIQUEMENT depuis l’OCR

- validate_customer_identity :
  → utiliser l’objet personal_info COMPLET issu de get_customer

- verify_capacity :
  → passer UNIQUEMENT le tableau loans (pas tout le document client)

- prepare_credit_request :
  → amount : le montant numérique (ex. 20000.0) issu de l'input utilisateur.
  → repayment_period : la durée en mois (ex. 24) issue de l'input utilisateur.
  → user_input_details_json : JSON contenant UNIQUEMENT les détails (ex: habitat_options, chevaux, etat_vehicule). NE PAS inclure de chemins de fichiers PDF ici.
  → personal_info_json = {"personal_info": {"age": <age>}}
  → ocr_data_json = sortie OCR (sans modification)

====================
IMPORTANT
====================
- NE PAS appeler les outils plusieurs fois inutilement.
- Utiliser des JSON PETITS (ne pas passer tout l’objet client).
- NE PAS inclure de chemins de fichiers dans les arguments des outils.
- S’assurer que le JSON est complet (pas de troncature).

====================
RÈGLES DE REJET
====================
Rejeter si :
- fiche de paie invalide
- identité invalide
- capacité négative

====================
ÉTAPE 10 — submit_supervisor_report (CRITIQUE)
====================
Limite de contexte (~4096 tokens) : ne PAS mettre de JSON volumineux dans accounts_info_json,
structured_request_json ou credit_history_str — utiliser "{}", "[]", "" afin que l’appel soit parsable ;
le backend fusionnera avec la base de données et prepare_credit_request.

client_info_summary (en français, ton professionnel bancaire — C’EST ICI que vont les détails) :
- Pas de style informel ou télégraphique ("Pipeline OK"). Utiliser des phrases complètes et des sections numérotées comme dans la docstring de l’outil.
- Couvrir :
  1. Validation de la fiche de paie
  2. Correspondance de l’identité
  3. Comparaison salaire OCR vs base de données
  4. Mise à jour DTI
  5. Vérification de la capacité
  6. Type de crédit / montant / durée + indicateurs clés issus de prepare_credit_request si disponibles
  7. Conclusion : soit dossier prêt pour étude financière (sous réserve de contrôles internes), soit rejet avec cause claire liée aux sections 1–5
- Utiliser uniquement des faits issus des outils précédents ; ne jamais inventer de montants ou identifiants.

Autres champs :
- validation_warnings_json : **CRITIQUE** Si le dossier est rejeté précipitamment (Fiche obsolète, Identité fausse, Capacité négative, etc.), tu DOIS obligatoirement placer ici la cause du rejet (ex: `["Nom/prénom ne correspond pas au dossier client."]`). Si tout est vert, laisse `[]`.
- accounts_info_json : "{}"
- structured_request_json : "{}"
- credit_history_str : ""

ARRÊT TECHNIQUE : après l’appel à submit_supervisor_report, l’exécution de l’agent s’arrête (aucun autre outil ne sera invoqué).

RAPPORT DÉTAILLÉ (backend) : un second modèle (Llama 70B / service rapport) reçoit ensuite toutes les sorties d’outils pour la synthèse professionnelle.
Tu peux donc garder client_info_summary court dans submit_supervisor_report si le contexte est limité ; le rapport long est généré côté service rapport.

Rejets anticipés (même comportement : submit seul, sections « non applicable » pour ce qui n’a pas été vérifié) :
- Étape 2 (Date) : si `validate_payslip_date` ≠ « VALIDE » → Arrêt immédiat ! Tu DOIS passer le message d'erreur dans l'argument `validation_warnings_json` de `submit_supervisor_report` (ex: `["Fiche obsolète"]`).
- Étape 4 (Identité) : si `validate_customer_identity` ≠ « VALIDE » → Arrêt immédiat ! Tu DOIS passer le message de l'outil identité dans l'argument `validation_warnings_json` de `submit_supervisor_report` (ex: `["Nom/prénom ne correspond pas"]`). Ne pas appeler `compare_salary_ocr_vs_db`.
- Étape 7 (Capacité) : si `verify_capacity` ≠ « OK » → Arrêt immédiat ! Tu DOIS passer le motif de refus dans l'argument `validation_warnings_json` de `submit_supervisor_report` (ex: `["Capacité d'engagement insuffisante"]`).
'''

tools = [
    extract_payslip_data_tool,
    validate_payslip_date,
    validate_customer_identity,
    get_customer,
    compare_salary_ocr_vs_db,
    update_customer_salary,
    update_dti_from_payslip,
    verify_capacity,
    get_bank_params,
    prepare_credit_request,
    submit_supervisor_report,
]

# Allow more tool rounds for complex flows (LangGraph)
_AGENT_CONFIG = {"recursion_limit": int(os.environ.get("FASTFIN_AGENT_RECURSION_LIMIT", "50"))}

agent = create_react_agent(llm, tools=tools)


def _canonical_tool_outputs_from_messages(messages) -> Tuple[str, str, str, str]:
    """
    À partir de tous les messages des outils, sélectionner les sorties OCR, client et prepare_credit_request qui sont cohérentes.
    Évite d’utiliser un identifiant get_customer halluciné ou une date de validate_payslip_date incorrecte comme sources de données
    """
    ocr_chunks: list = []
    cust_chunks: list = []
    prepare_chunks: list = []
    bank_str = ""

    for msg in messages or []:
        if not (hasattr(msg, "name") and hasattr(msg, "content")):
            continue
        tool_name = getattr(msg, "name", "")
        content = (getattr(msg, "content", None) or "").strip()
        if not content:
            continue
        if tool_name == "extract_payslip_data_tool":
            ocr_chunks.append(content)
        elif tool_name == "get_customer":
            cust_chunks.append(content)
        elif tool_name == "prepare_credit_request":
            prepare_chunks.append(content)
        elif tool_name == "get_bank_params":
            bank_str = content

    ocr_data_str = "{}"
    ocr_data: dict = {}
    for s in reversed(ocr_chunks):
        try:
            d = json.loads(s)
            if isinstance(d, dict) and d.get("numero_compte"):
                ocr_data_str = s
                ocr_data = d
                break
        except Exception:
            continue

    want_id = str(ocr_data.get("numero_compte") or "").strip()

    def _customer_ok(s: str) -> bool:
        try:
            c = json.loads(s)
        except Exception:
            return False
        return (
            isinstance(c, dict)
            and not c.get("error")
            and bool(c.get("_id"))
        )

    customer_db_str = "{}"
    for s in reversed(cust_chunks):
        if not _customer_ok(s):
            continue
        c = json.loads(s)
        if want_id and str(c.get("_id")) != want_id:
            continue
        customer_db_str = s
        break
    else:
        for s in reversed(cust_chunks):
            if _customer_ok(s):
                customer_db_str = s
                break

    prepare_credit_out = ""
    for s in reversed(prepare_chunks):
        try:
            p = json.loads(s)
            if not isinstance(p, dict):
                continue
            rab = p.get("RAB")
            rev_a = p.get("revenu_brut_annuel")
            inc_m = p.get("income_brut_monthly")
            ok = False
            for v in (rab, rev_a, inc_m):
                if v is None:
                    continue
                try:
                    if float(v) > 0:
                        ok = True
                        break
                except (TypeError, ValueError):
                    pass
            if ok:
                prepare_credit_out = s
                break
        except Exception:
            continue
    if not prepare_credit_out and prepare_chunks:
        prepare_credit_out = prepare_chunks[-1]

    if not bank_str:
        bank_str = "{}"

    return ocr_data_str, customer_db_str, prepare_credit_out, bank_str






def _assistant_text_content(msg) -> str:
    """Normalize LangChain message content to a single string."""
    c = getattr(msg, "content", None)
    if c is None:
        return ""
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, list):
        parts = []
        for block in c:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts).strip()
    return str(c).strip()


def _parse_report_llm_json(text: str) -> Optional[Dict[str, Any]]:
    """Extrait un objet JSON depuis la réponse."""
    if not text or not str(text).strip():
        return None
    raw = str(text).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _recover_report_from_assistant_messages(messages) -> dict:
    """
    Identifie si le rapport est présent en texte dans le contenu de l'assistant (fallback).
    """
    for msg in reversed(messages or []):
        if not isinstance(msg, AIMessage):
            continue
        text = _assistant_text_content(msg)
        obj = _parse_report_llm_json(text)
        if obj and (obj.get("client_info_summary") or obj.get("decision_reason")):
             return obj
    return {}



def run_supervisor(state: AgentState) -> dict:
    req_details = {
        "pdf_path": state.get("details", {}).get("fiche_paie_path", ""),
        "type_credit": state.get("type_credit"),
        "amount": state.get("amount"),
        "repayment_period": state.get("repayment_period"),
        "user_input_options": state.get("details", {}),
    }

    human_msg = (
        "Process this credit application end-to-end using your tools. "
        "Credit type and amount are in the JSON below.\n"
        f"{json.dumps(req_details, indent=2, ensure_ascii=False)}"
    )

    try:
        response = agent.invoke(
            {"messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=human_msg)]},
            config=_AGENT_CONFIG,
        )

        msgs = response.get("messages", [])

        # Agrégation des sorties d’outils déjà produites par l’agent (pas d’invoke Python supplémentaire).
        ocr_data_str, customer_db_str, prepare_credit_out, _bank_params_str = (
            _canonical_tool_outputs_from_messages(msgs)
        )

        val_warnings = []
        acc_info = {}
        client_info = ""
        credit_history = ""

        struct_req = {}
        if prepare_credit_out:
            try:
                struct_req = json.loads(prepare_credit_out)
            except Exception:
                struct_req = {}

        for msg in reversed(msgs):
            if hasattr(msg, "tool_calls") and getattr(msg, "tool_calls"):
                for tool_call in msg.tool_calls:
                    if tool_call.get("name") == "submit_supervisor_report":
                        args = tool_call.get("args", {})
                        try:
                            llm_warnings = json.loads(args.get("validation_warnings_json", "[]"))
                            if isinstance(llm_warnings, list):
                                val_warnings = val_warnings + llm_warnings
                        except Exception:
                            pass
                        try:
                            acc_info = json.loads(args.get("accounts_info_json", "{}"))
                        except Exception:
                            acc_info = {}
                        client_info = args.get("client_info_summary", "")
                        credit_history = args.get("credit_history_str", "")
                        break

        if not (client_info or "").strip() and not val_warnings and not acc_info:
            val_warnings = ["Supervisor report was not emitted by agent."]

        # HARD ENFORCEMENT: Check literal tool messages to see if any failure occurred 
        # (in case the LLM ignored strict instructions and skipped populating validation_warnings_json)
        for msg in msgs:
            if getattr(msg, "name", None) in ["validate_payslip_date", "validate_customer_identity"]:
                ans = getattr(msg, "content", "").strip()
                if ans and ans != "VALIDE":
                    if ans not in val_warnings:
                        val_warnings.append(ans)
            elif getattr(msg, "name", None) == "verify_capacity":
                ans = getattr(msg, "content", "").strip()
                if ans and ans != "OK":
                    if ans not in val_warnings:
                        val_warnings.append(ans)

        # Fallback (optional) : recover report from AI messages if no tool was called
        if not (client_info or "").strip() and not val_warnings:
             recovered = _recover_report_from_assistant_messages(msgs)
             if recovered:
                 client_info = recovered.get("client_info_summary", "")
                #  credit_history = recovered.get("credit_history_summary", "")
                 if recovered.get("validation_warnings"):
                      val_warnings = val_warnings + recovered["validation_warnings"]

        print("client info ", client_info)
        print("accounts info ", acc_info)
        print("validation warnings ", val_warnings)
        print("structured request ", struct_req)
        # print("credit history ", credit_history)

        # Extracted `want_id` from the canonical tool outputs earlier
        want_id = ""
        try:
            if ocr_data_str and ocr_data_str != "{}":
                want_id = json.loads(ocr_data_str).get("numero_compte", "")
            if not want_id and customer_db_str and customer_db_str != "{}":
                want_id = str(json.loads(customer_db_str).get("_id", ""))
        except Exception:
            pass

        connected_id = str(state.get("client_id", "")).strip()
        # ID Verification against connected user
        if connected_id and want_id and connected_id != want_id and connected_id != "API_Client":
            rejection_msg = "Rejet: L'identifiant du compte sur la fiche de paie ne correspond pas à l'utilisateur connecté."
            if rejection_msg not in val_warnings:
                val_warnings.append(rejection_msg)
            client_info = "Échec d'authentification: Le document fourni appartient à un autre utilisateur."
            struct_req = {}

        try:
            from bson import ObjectId
        except ImportError:
            pass
        cid = want_id if want_id else None

        return {
            "customer_id": cid,
            "client_info": client_info,
            "accounts_info": acc_info,
            "validation_warnings": val_warnings,
            "structured_request": struct_req,
            # "credit_history": credit_history,
        }

    except Exception as e:
        return {"validation_warnings": [f"Erreur d'exécution de l'agent: {str(e)}"]}
