import sys
import os
import re
from typing import Optional
import unicodedata
from datetime import datetime, date
from decimal import Decimal
import json
import logging
import functools
from langchain_core.tools import tool

# Set FASTFIN_DEBUG_TOOLS=0 to disable per-tool stdout tracing
_TOOL_DEBUG = os.environ.get("FASTFIN_DEBUG_TOOLS", "1").strip().lower() not in ("0", "false", "no")
_TOOL_DEBUG_MAX = int(os.environ.get("FASTFIN_DEBUG_TOOLS_MAXLEN", "6000"))


def _trace_tool(fn):
    """Afficher le nom de l’outil, les entrées et la sortie dans stderr (avec vidage forcé pour un débogage en temps réel)"""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not _TOOL_DEBUG:
            return fn(*args, **kwargs)
        name = getattr(fn, "__name__", repr(fn))
        print(f"\n{'=' * 72}", flush=True)
        print(f"[TOOL IN]  {name}", flush=True)
        if args:
            print(f"  args:   {args!r}", flush=True)
        if kwargs:
            print(f"  kwargs: {kwargs!r}", flush=True)
        try:
            out = fn(*args, **kwargs)
        except Exception as e:
            print(f"[TOOL ERR] {name}: {type(e).__name__}: {e}", flush=True)
            print(f"{'=' * 72}\n", flush=True)
            raise
        s = str(out)
        if len(s) > _TOOL_DEBUG_MAX:
            s = s[:_TOOL_DEBUG_MAX] + f"\n... [truncated, total {len(str(out))} chars]"
        print(f"[TOOL OUT] {name}", flush=True)
        print(s, flush=True)
        print(f"{'=' * 72}\n", flush=True)
        return out

    return wrapper

# Insert relative import to mcp_server safely
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from bd.mcp_server import mcp_handle

# Import OCR to wrap it as a tool
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supervisor.ocr_tool import extract_payslip_data


def _json_default_bson(obj):
    """Rendre les valeurs MongoDB / BSON sérialisables en JSON pour json.dumps"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    try:
        from bson import ObjectId
        if isinstance(obj, ObjectId):
            return str(obj)
    except Exception:
        pass
    try:
        from bson.decimal128 import Decimal128
        if isinstance(obj, Decimal128):
            return float(obj.to_decimal())
    except Exception:
        pass
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    # Last resort: stringify unknown BSON / custom types so the tool never crashes
    return str(obj)

#Working
@tool
@_trace_tool
def extract_payslip_data_tool(pdf_path: str) -> str:
    """
    Extrait les données (JSON string) d'une fiche de paie PDF en utilisant OCR. 
    Retourne un string JSON contenant solde, nom, etc.
    """
    try:
        data = extract_payslip_data(pdf_path)
        return json.dumps(data, ensure_ascii=False) if data else "Erreur d'extraction OCR"
    except Exception as e:
        return f"Erreur fatale de l'OCR: {str(e)}"

#Working
@tool
@_trace_tool
def validate_payslip_date(date_str: str) -> str:
    """
    Vérifie si la date (ex: M/D/YYYY ou DD/MM/YYYY) appartient au mois en cours ou au mois précédent.
    Retourne « VALIDE » si ok, sinon un message d’échec (fiche obsolète, format, etc.).

    Si la sortie n’est pas exactement « VALIDE », ne pas enchaîner get_customer ni les étapes suivantes —
    terminer par submit_supervisor_report (rejet) avec ce message et les données OCR disponibles.
    """
    if not date_str:
        return "Date introuvable sur la fiche de paie."
    
    try:
        date_str = date_str.replace('-', '/')
        payslip_date = None
        
        # Try multiple common formats
        for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                payslip_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                pass
                
        if not payslip_date:
            return f"Format de date non reconnu : {date_str}"
        
        today = datetime.today()
        current_year = today.year
        current_month = today.month
        
        if current_month == 1:
            prev_month = 12
            prev_year = current_year - 1
        else:
            prev_month = current_month - 1
            prev_year = current_year
            
        payslip_month = payslip_date.month
        payslip_year = payslip_date.year
        
        if (payslip_year == current_year and payslip_month == current_month) or \
           (payslip_year == prev_year and payslip_month == prev_month):
            return "VALIDE"
        else:
            return "La fiche de paie est obsolète (elle doit dater de ce mois-ci ou du mois dernier)."
    except ValueError:
        return f"Format de date non reconnu : {date_str}"

#Working
@tool
@_trace_tool
def get_customer(numero_compte: str) -> str:
    """
    Récupérer les informations du client depuis MongoDB sous format JSON string.
    Inclut uniquement les prêts non remboursés (loan_paid_back=False) dans 'loans'.
    """
    if not numero_compte:
        return "{}"

    oid_str = str(numero_compte).strip()
    if not re.fullmatch(r"[a-fA-F0-9]{24}", oid_str):
        return json.dumps({
            "error": "numero_compte_invalide",
            "message": "L'identifiant doit être exactement le champ 'numero_compte' de l'extrait OCR (24 caractères hexadécimaux). Ne pas en inventer un autre.",
            "reçu": oid_str,
        }, ensure_ascii=False)

    from bson import ObjectId
    from bson.errors import InvalidId

    or_clauses = [{"_id": oid_str}]
    try:
        or_clauses.insert(0, {"_id": ObjectId(oid_str)})
    except InvalidId:
        pass

    req = {
        "action": "fetch",
        "collection": "customers",
        "filter": {"$or": or_clauses},
    }
    resp = mcp_handle(req)
    rows = resp.get("data") if resp and resp.get("status") == "success" else None
    if rows and len(rows) > 0:
        raw = dict(rows[0])
        loans_all = raw.get("loans", [])
        loans_unpaid = [loan for loan in loans_all if not loan.get("loan_paid_back", False)]

        data = {
            "_id": str(raw["_id"]),
            "personal_info": raw.get("personal_info", {}),
            "employment": raw.get("employment", {}),
            "loans": loans_unpaid,
        }
        return json.dumps(data, ensure_ascii=False, default=_json_default_bson)

    return "{}"

#Working
def _normalize_identity_for_match(value) -> str:
    """Same rules as supervisor/agent.py: robust token comparison."""
    txt = unicodedata.normalize("NFKD", str(value or ""))
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = txt.upper()
    txt = re.sub(r"[^A-Z0-9\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

#Working
def _digits_only(s) -> str:
    return re.sub(r"\D", "", str(s or ""))

#Working
@tool
@_trace_tool
def validate_customer_identity(nom_prenom: str, cin: str, personal_info: dict) -> str:
    """
    Vérifie l'identité du client à partir de :
    - Nom & prénom (OCR)
    - CIN (OCR, 8 chiffres attendus si présent en base)
    - Données client (personal_info)

    Retourne exactement « VALIDE » si tout correspond.
    Sinon : un ou plusieurs messages d’erreur séparés par « | » (ex. « Nom/prénom ne correspond pas au dossier client. »).

    Comportement attendu côté superviseur (comme pour validate_payslip_date) :
    si la sortie n’est pas exactement « VALIDE », ne pas appeler compare_salary_ocr_vs_db,
    verify_capacity, get_bank_params ni prepare_credit_request — terminer par submit_supervisor_report
    avec rejet motivé (OCR + get_customer + ce message).
    """
    if not isinstance(personal_info, dict):
        personal_info = {}

    if not nom_prenom and not cin:
        return "Informations insuffisantes pour vérifier l'identité (nom_prenom et cin absents)."

    ocr_full = _normalize_identity_for_match(nom_prenom)
    db_nom = _normalize_identity_for_match(personal_info.get("nom", ""))
    db_prenom = _normalize_identity_for_match(personal_info.get("prenom", ""))
    ocr_tokens = set(ocr_full.split()) if ocr_full else set()

    extracted_cin = _digits_only(cin)
    expected_cin = _digits_only(personal_info.get("cin", ""))

    errors = []

    # Nom / prénom : les deux tokens DB doivent apparaître comme mots entiers dans l'OCR
    if db_nom and db_prenom:
        if not ocr_full:
            errors.append("Nom/prénom introuvable sur la fiche de paie.")
        elif not (db_nom in ocr_tokens and db_prenom in ocr_tokens):
            errors.append("Nom/prénom ne correspond pas au dossier client.")
    elif db_nom or db_prenom:
        errors.append("Dossier client incomplet (nom ou prénom manquant en base).")
    else:
        errors.append(
            "personal_info incomplet : passer l'objet 'personal_info' COMPLET retourné par get_customer "
            "(champs 'nom' et 'prenom' obligatoires). Ne pas tronquer à {age} seul."
        )

    # CIN : si la base a un CIN, l'OCR doit le lire et matcher (8 chiffres si la base en a 8)
    if expected_cin:
        if len(expected_cin) == 8:
            if len(extracted_cin) != 8:
                errors.append("CIN sur fiche de paie absent ou nombre de chiffres incorrect (8 attendus).")
            elif extracted_cin != expected_cin:
                errors.append("CIN ne correspond pas au dossier client.")
        else:
            if extracted_cin != expected_cin:
                errors.append("CIN ne correspond pas au dossier client.")

    if not errors:
        return "VALIDE"
    return " | ".join(errors)


def _parse_salary_number(value) -> Optional[float]:
    """Parse OCR/DB salary string or number to float TND."""
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        return None


@tool
@_trace_tool
def compare_salary_ocr_vs_db(ocr_salary_net: str, db_monthly_income: float) -> str:
    """
    Compare le salaire net issu de l'OCR (chaîne, ex. "1244,974") avec employment.monthly_income en base.

    Retourne une chaîne JSON, ex.:
    {"needs_update": true, "ocr_value": 1244.974, "db_value": 1244.974, "diff": 0.0, "threshold_tnd": 1.0}

    - Si needs_update est true (écart absolu > threshold_tnd), appelez ensuite update_customer_salary avec le salaire OCR.
    - Si needs_update est false, ne appelez PAS update_customer_salary pour ce motif.

    Seuil par défaut : 1.0 TND (modifiable via variable d'environnement SALARY_DIFF_THRESHOLD_TND).
    """
    threshold = float(os.environ.get("SALARY_DIFF_THRESHOLD_TND", "1.0"))
    ocr = _parse_salary_number(ocr_salary_net)
    try:
        dbv = float(db_monthly_income) if db_monthly_income is not None else None
    except (ValueError, TypeError):
        dbv = None

    if ocr is None or dbv is None:
        out = {
            "needs_update": False,
            "reason": "valeur_manquante_ou_invalide",
            "ocr_value": ocr,
            "db_value": dbv,
            "diff": None,
            "threshold_tnd": threshold,
        }
        return json.dumps(out, ensure_ascii=False)

    diff = abs(ocr - dbv)
    needs = diff > threshold
    out = {
        "needs_update": needs,
        "ocr_value": ocr,
        "db_value": dbv,
        "diff": diff,
        "threshold_tnd": threshold,
    }
    return json.dumps(out, ensure_ascii=False)


@tool
@_trace_tool
def update_customer_salary(customer_id: str, new_salary: float, new_annual_income: float) -> str:
    """
    Met à jour le salaire net (monthly_income), l'annualisation, et le DTI dans MongoDB.
    Le nouveau DTI est calculé automatiquement à partir de l'ancien DTI et du nouveau salaire.
    Retourne un message de succès.
    """
    try:
        from bson import ObjectId
        filter_id = ObjectId(customer_id) if isinstance(customer_id, str) and len(customer_id) == 24 else customer_id
    except Exception:
        filter_id = customer_id
        
    # 1. Fetch current customer to get old DTI and old salary
    req_fetch = {
        "action": "fetch",
        "collection": "customers",
        "filter": {"_id": filter_id}
    }
    resp_fetch = mcp_handle(req_fetch)
    
    new_dti = 0.0
    if resp_fetch and resp_fetch.get("status") == "success" and resp_fetch.get("data"):
        cust = resp_fetch["data"][0]
        emp = cust.get("employment", {})
        old_salary = float(emp.get("monthly_income") or 0.0)
        old_dti = float(emp.get("debt_to_income_ratio") or 0.0)
        
        if old_salary > 0 and new_salary > 0:
            # Step 1: Calculate total current debts based on old DTI
            # Dettes = Salaire_Ancien * (Ancien_DTI / 100)
            current_debts = old_salary * (old_dti / 100.0)
            # Step 2: Calculate new DTI based on same debts but new salary
            # Nouveau_DTI = (Dettes / Nouveau_Salaire) * 100
            new_dti = (current_debts / new_salary) * 100.0
        else:
            new_dti = old_dti # Fallback if calculation is not possible

    # 2. Update record
    req_update = {
        "action": "update",
        "collection": "customers",
        "filter": {"_id": filter_id},
        "data": {
            "employment.monthly_income": new_salary,
            "employment.annual_income": new_annual_income,
            "employment.debt_to_income_ratio": new_dti
        }
    }
    mcp_handle(req_update)
    return f"Mise à jour réussie (Ancien DTI -> Nouveau DTI: {new_dti:.2f}%)."

@tool
@_trace_tool
def update_dti_from_payslip(
    customer_id: str,
    net_salary: float,
    old_dti_ratio: float,
    new_payslip_charges: float
) -> str:
    """
    Met à jour le DTI du client en évitant le double comptage des charges.

    Logique :
    1. Calcule les dettes actuelles via old_dti
    2. Simule un DTI avec ajout des nouvelles charges
    3. Si l'impact est trop élevé → charges probablement déjà incluses → ne pas recalculer
    4. Sinon → recalcul et update

    Seuils :
    - Variation négligeable : 1%
    - Détection double comptage : +10% d'écart DTI
    """

    try:
        from bson import ObjectId
        filter_id = ObjectId(customer_id) if isinstance(customer_id, str) and len(customer_id) == 24 else customer_id
    except Exception:
        filter_id = customer_id

    if net_salary <= 0:
        return "Erreur: Le salaire net doit être supérieur à 0."

    # =========================
    # 1. DETTES ACTUELLES
    # =========================
    dettes_existantes = old_dti_ratio * net_salary

    # =========================
    # 2. SIMULATION AVEC NOUVELLES CHARGES
    # =========================
    dettes_totales = dettes_existantes + new_payslip_charges
    nouveau_dti_ratio = dettes_totales / net_salary

    # =========================
    # 3. DETECTION DOUBLE COMPTAGE
    # =========================
    # Si le DTI explose trop → charges déjà incluses
    if abs(nouveau_dti_ratio - old_dti_ratio) > 0.10:
        return (
            f"Aucune mise à jour : les charges ({new_payslip_charges} TND) semblent déjà incluses dans le DTI actuel. "
            f"(DTI actuel={old_dti_ratio:.4f}, DTI simulé={nouveau_dti_ratio:.4f})"
        )

    # =========================
    # 4. VARIATION NEGLIGEABLE
    # =========================
    if abs(nouveau_dti_ratio - old_dti_ratio) <= 0.01:
        return (
            f"DTI inchangé (variation faible). "
            f"(Ancien={old_dti_ratio:.4f}, Nouveau={nouveau_dti_ratio:.4f})"
        )

    # =========================
    # 5. UPDATE MONGO
    # =========================
    req_update = {
        "action": "update",
        "collection": "customers",
        "filter": {"_id": filter_id},
        "data": {
            "employment.debt_to_income_ratio": nouveau_dti_ratio
        }
    }

    mcp_handle(req_update)

    return (
        f"DTI mis à jour avec succès : "
        f"Ancien={old_dti_ratio:.4f} -> Nouveau={nouveau_dti_ratio:.4f}"
    )

@tool
@_trace_tool
def verify_capacity(salary_net: str, credit_entreprise: str, loans_json: str) -> str:
    """
    Vérifie la capacité d'engagement :
    40% * salary_net - credit_entreprise - loans_bank_engagement.

    loans_json : JSON du seul tableau `loans` (liste), ou `{"loans": [...]}`, ou ancien document client (on lit seulement `loans`).
    Ne pas envoyer tout le client si possible — seule la liste des prêts est utilisée.

    Retourne exactement « OK » si la capacité restante est ≥ 0.
    Sinon : message multi-lignes expliquant pourquoi la capacité est négative (détail 40 %, crédit entreprise,
    mensualités prêts actifs, formule) ou message d’erreur de conversion.

    Comportement attendu côté superviseur (comme date / identité) :
    si la sortie n’est pas exactement « OK », ne pas appeler get_bank_params ni prepare_credit_request —
    terminer par submit_supervisor_report avec rejet motivé.
    """
    loans = []
    try:
        raw = json.loads(loans_json) if loans_json and str(loans_json).strip() else []
        if isinstance(raw, list):
            loans = raw
        elif isinstance(raw, dict):
            loans = raw.get("loans", [])
    except Exception:
        loans = []

    loans_bank_engagement = 0.0
    
    for loan in loans:
        if not loan.get("loan_paid_back", True):
            loans_bank_engagement += float(loan.get("monthly_amount", 0.0) or loan.get("installment", 0.0))
            
    try:
        s_net = float(str(salary_net).replace(',', '.').replace(' ', ''))
        av = float(str(credit_entreprise).replace(',', '.').replace(' ', '')) if credit_entreprise and str(credit_entreprise).strip() else 0.0
    except ValueError:
        return "Erreur de conversion numérique du salaire ou du crédit entreprise."
            
    ceiling_40 = 0.40 * s_net
    capacity = ceiling_40 - av - loans_bank_engagement

    n_active = sum(
        1
        for loan in loans
        if isinstance(loan, dict) and not loan.get("loan_paid_back", True)
    )

    if capacity < 0:
        parts = [
            f"Capacité d'engagement insuffisante : le reste disponible est négatif ({capacity:.2f} TND).",
            "",
            "Détail du calcul (règle banque : 40 % du salaire net − crédit entreprise − mensualités des prêts non soldés) :",
            f"  • Plafond 40 % du salaire net : {ceiling_40:.2f} TND (salaire net retenu : {s_net:.2f} TND).",
            f"  • Crédit entreprise / autres dettes mensuelles déduites : {av:.2f} TND.",
            f"  • Total mensualités prêts en cours (prêts non remboursés, n={n_active}) : {loans_bank_engagement:.2f} TND.",
            "",
            f"Formule : {ceiling_40:.2f} − {av:.2f} − {loans_bank_engagement:.2f} = {capacity:.2f} TND.",
            "La capacité est négative car le plafond 40 % est dépassé par la somme des charges déjà engagées (crédit entreprise + échéances de prêts).",
        ]
        return "\n".join(parts)
    else:
        return "OK"

#Working
@tool
@_trace_tool
def get_bank_params() -> str:
    """
    Récupère la table bank_params incluant le TMM et marges. Retourne JSON string.
    """
    req_fetch = {
        "action": "fetch",
        "collection": "bank_params",
        "filter": {"param_type": "global_rates"}
    }
    resp = mcp_handle(req_fetch)
    if resp.get("status") == "success" and resp.get("data"):
        data = resp.get("data")[0]
        data["_id"] = str(data["_id"])
        return json.dumps(data)
    
    default_params = {
        "param_type": "global_rates",
        "tmm": 0.0699,
        "marge_additionnelle_consommation": 0.05,
        "marge_additionnelle_amenagement": 0.0375,
        "marge_additionnelle_voiture": 0.035
    }
    mcp_handle({
        "action": "insert",
        "collection": "bank_params",
        "data": default_params
    })
    return json.dumps(default_params)

def _age_from_personal_info_json(personal_info_json: str) -> int:
    """
    Attendu : '{"personal_info": {"age": 23}}' uniquement (ou raccourci '{"age": 23}').
    """
    default_age = 30
    if not personal_info_json or not str(personal_info_json).strip():
        return default_age
    try:
        raw = json.loads(personal_info_json)
    except Exception:
        return default_age
    if not isinstance(raw, dict):
        return default_age
    if "personal_info" in raw and isinstance(raw["personal_info"], dict):
        age = raw["personal_info"].get("age", default_age)
    else:
        age = raw.get("age", default_age)
    try:
        return int(age)
    except (TypeError, ValueError):
        return default_age


#Working
@tool
@_trace_tool
def prepare_credit_request(
    credit_type: str,
    amount: float,
    repayment_period: int,
    user_input_details_json: str,
    ocr_data_json: str,
    personal_info_json: str,
    bank_params_json: str,
) -> str:
    """
    Prépare le payload JSON final structuré basé sur le type de crédit.
    amount: Montant demandé (ex: 20000.0)
    repayment_period: Durée en MOIS (ex: 24)
    user_input_details_json: JSON contenant les détails spécifiques (habitat_options, chevaux, etc.)
    """
    try:
        details = json.loads(user_input_details_json)
        ocr_data = json.loads(ocr_data_json)
        bank_params = json.loads(bank_params_json)
    except Exception:
        return "{}"

    age = _age_from_personal_info_json(personal_info_json)

    try:
        salary_net = float(str(ocr_data.get("salary_net", "0")).replace(',', '.'))
        autres_dettes = float(str(ocr_data.get("credit_entreprise", "0")).replace(',', '.'))
    except (ValueError, TypeError):
        salary_net = 0.0
        autres_dettes = 0.0
    
    payload = {}
    if credit_type == "Crédit Habitat":
        options = details.get("habitat_options", {})
        
        def extract_cat_dur(cat_str):
            if not cat_str or cat_str == "Choisissez une catégorie":
                return None, None
            cat_match = re.search(r'([A-Z])', str(cat_str))
            dur_match = re.search(r'(\d+)', str(cat_str))
            cat = cat_match.group(1) if cat_match else "N"
            dur = int(dur_match.group(1)) if dur_match else 1
            return cat, dur
            
        celc_cat, celc_dur = extract_cat_dur(options.get("categorie_complementaire_str", ""))
        jedid_cat, jedid_dur = extract_cat_dur(options.get("categorie_jedid_str", ""))
        
        choose_normal = options.get("credit_normal", False)
        choose_celc = options.get("credit_complementaire", False)
        choose_jedid = options.get("credit_jedid", False)
        
        payload = {
            "project_cost": amount,
            "age": age,
            "income_brut_monthly": salary_net, 
            "other_debts_monthly": autres_dettes,
            "autofinancement_pct": 20,
            "choose_normal_credit": choose_normal,
            "choose_complementary_credit": choose_celc,
            "choose_eljedid_credit": choose_jedid,
            "choose_direct_credit": options.get("credit_direct", True)
        }
        
        if choose_celc:
            payload["celc_category"] = celc_cat or "N"
            payload["celc_duration"] = celc_dur or 4
            
        if choose_jedid:
            payload["eljedid_category"] = jedid_cat or "B"
            payload["eljedid_duration"] = jedid_dur or 2
    
    elif credit_type == "Crédit consommation":
        payload = {
            "CCD": amount,
            "age": age,
            "duration_choice_years": float(repayment_period) / 12.0,
            "RAB": salary_net * 12,
            "autres_dettes_mensuelles": autres_dettes,
            "TMM": bank_params.get("tmm", 0.0699),
            "marge_additionnelle": bank_params.get("marge_additionnelle_consommation", 0.05)
        }
        
    elif credit_type == "Crédit aménagement":
        payload = {
            "CCD": amount,
            "age": age,
            "duration_choice_years": float(repayment_period) / 12.0,
            "RAB": salary_net * 12,
            "autres_dettes_mensuelles": autres_dettes,
            "TMM": bank_params.get("tmm", 0.0699),
            "marge_additionnelle": bank_params.get("marge_additionnelle_amenagement", 0.0375)
        }
        
    elif credit_type == "Crédit BH auto":
        payload = {
            "prix_voiture": amount,
            "age": age,
            "duree_choisie": float(repayment_period) / 12.0,
            "revenu_brut_annuel": salary_net * 12,
            "autres_dettes_mensuelles": autres_dettes,
            "chevaux": int(details.get("chevaux", 4)),
            "etat_vehicule": details.get("etat_vehicule", "Neuf"),
            "taux_moyen_du_marche": bank_params.get("tmm", 0.0699),
            "marge_additionnelle": bank_params.get("marge_additionnelle_voiture", 0.035)
        }
        
    return json.dumps(payload, ensure_ascii=False)

# Working — return_direct=True: LangGraph arrête le ReAct après cet outil (sinon le LLM peut rappeler 7/8/…).
@tool(return_direct=True)
@_trace_tool
def submit_supervisor_report(
    client_info_summary: str,
    accounts_info_json: str = "{}",
    validation_warnings_json: str = "[]",
    structured_request_json: str = "{}",
    credit_history_str: str = "",
) -> str:
    """
    APPELER CET OUTIL UNE SEULE FOIS EN DERNIERE ÉTAPE. Après exécution, l’agent s’arrête : ne pas appeler d’autres outils.

    Le résumé lisible pour le conseiller va dans `client_info_summary` (texte structuré, ton professionnel banque).
    Les autres champs JSON doivent rester courts (souvent "{}" / "[]" / "") pour éviter la troncation du modèle ;
    le serveur peut compléter compte, historique crédit et payload structuré à partir des sorties précédentes.

    --- client_info_summary (obligatoire, style professionnel) ---
    Rédiger en français, phrases complètes, vocabulaire bancaire, sans jargon « pipeline » ni « OK » informel.
    S’appuyer UNIQUEMENT sur les résultats des outils déjà appelés (ne rien inventer).

    Structure type (adapter selon le parcours réel ; sauter les blocs non applicables) :

    1. Document de rémunération : indiquer si la date de paiement est valide, le salaire net relevé (OCR),
       et toute retenue / crédit entreprise pertinent pour la capacité.
    2. Dossier client et identité : concordance identité (nom, prénom, CIN) entre fiche de paie et base ;
       mentionner l’âge ou éléments clés du profil si utiles à la décision.
    3. Cohérence des revenus : comparaison salaire OCR vs base (écart ou alignement ; mise à jour salaire si effectuée).
    4. Capacité de remboursement : synthèse du résultat de la vérification (favorable ou motif de rejet si applicable).
    5. Paramètres de la demande : type de crédit, montant et durée demandés ; rappel des grands ratios issus de
       prepare_credit_request (ex. RAB, CCD, TMM, marge) lorsqu’ils sont disponibles.
    6. Décision et suite : conclure explicitement sur l’une des deux issues :
       — Si toutes les vérifications sont favorables : indiquer que le dossier est prêt pour l’étude financière
         (transmission au service compétent), en précisant qu’il s’agit d’une validation préalable du flux superviseur
         et « sous réserve des contrôles complémentaires internes ».
       — Si le dossier est refusé à ce stade : indiquer le rejet et en expliquer clairement la cause
         (ex. fiche de paie non valide, identité non concordante, capacité insuffisante), en renvoyant aux constats
         des sections 1 à 4 sans formulation vague.

    En cas d’arrêt anticipé (fiche de paie, identité, capacité), le point 6 doit quand même formuler le rejet motivé ;
    compléter validation_warnings_json si un libellé court synthétique est utile.

    --- Autres arguments ---
    validation_warnings_json : tableau JSON de chaînes, ex. '[]' ou '["Motif précis"]'.
    accounts_info_json : de préférence "{}" ; le serveur peut enrichir numero_compte / solde depuis la DB.
    credit_history_str : de préférence "" ; le serveur peut injecter l’historique des prêts.
    structured_request_json : de préférence "{}" ; le serveur peut fusionner la sortie de prepare_credit_request.

    Retour : "REPORT_SUBMITTED_SUCCESSFULLY".
    """
    return "REPORT_SUBMITTED_SUCCESSFULLY"
