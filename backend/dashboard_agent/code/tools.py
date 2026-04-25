"""
MCP Tools — Banque Tunisienne
Architecture universelle : chaque tool accepte (cin, date_debut, date_fin)
→ mode global / par période / par client CIN / client + période
"""
import json, re
from bson import ObjectId
from langchain_core.tools import tool
from handler import fetch, count, aggregate
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════
# HELPERS INTERNES
# ═══════════════════════════════════════════════════════════════
def _clean(x):
    """Nettoie une valeur string."""
    if not x: return None
    s = str(x).replace('"','').replace('{','').replace('}','').strip()
    return s if s else None

def _parse_dates(d1_str, d2_str):
    """Convertit deux strings date en objets datetime."""
    d1 = datetime.strptime(d1_str.strip(), "%Y-%m-%d") if d1_str and d1_str.strip() else None
    d2 = datetime.strptime(d2_str.strip(), "%Y-%m-%d") if d2_str and d2_str.strip() else None
    return d1, d2

def _extract_args(raw_first, second="", third=""):
    """
    Normalise les arguments depuis n'importe quel format envoyé par l'agent :
    JSON string, dict, ou valeurs directes.
    Retourne (cin, date_debut, date_fin) tous nettoyés.
    """
    if isinstance(raw_first, dict):
        return (
            _clean(raw_first.get("cin", "")),
            _clean(raw_first.get("date_debut", "")),
            _clean(raw_first.get("date_fin", ""))
        )
    if isinstance(raw_first, str) and raw_first.strip().startswith("{"):
        try:
            d = json.loads(raw_first)
            return (
                _clean(d.get("cin", "")),
                _clean(d.get("date_debut", "")),
                _clean(d.get("date_fin", ""))
            )
        except Exception:
            pass
    # Valeurs directes
    return (
        _clean(raw_first) if raw_first else None,
        _clean(second)    if second    else None,
        _clean(third)     if third     else None,
    )

def _cin_to_customer_id(cin: str):
    """Résout CIN → customer_id MongoDB. Retourne None si introuvable."""
    if not cin:
        return None
    r = fetch("customers",
              filtre={"personal_info.cin": cin},
              projection={"_id": 1}, limit=1)
    return str(r[0]["_id"]) if r else None

def _build_date_match(d1, d2, field="date"):
    """Construit le filtre de date MongoDB."""
    if d1 and d2:
        return {field: {"$gte": d1, "$lte": d2 + timedelta(days=1)}}
    if d1:
        return {field: {"$gte": d1}}
    if d2:
        return {field: {"$lte": d2}}
    return {}

def _build_match(customer_id=None, d1=None, d2=None, date_field="date"):
    """Construit le filtre MongoDB combiné client + période."""
    m = {}
    if customer_id:
        m["customer_id"] = customer_id
    dm = _build_date_match(d1, d2, date_field)
    m.update(dm)
    return m

def _period_label(cin, d1_str, d2_str):
    """Génère le label du filtre appliqué."""
    parts = []
    if cin:    parts.append(f"CIN {cin}")
    if d1_str: parts.append(f"{d1_str} → {d2_str or '?'}")
    return " | ".join(parts) if parts else "Global"

def _get_account_numbers(customer_id: str):
    """Retourne les account_numbers d'un client."""
    accounts = fetch("accounts",
                     filtre={"customer_id": customer_id},
                     projection={"account_number": 1})
    return [a["account_number"] for a in accounts if a.get("account_number")]


# ═══════════════════════════════════════════════════════════════
# KPIs GLOBAUX
# ═══════════════════════════════════════════════════════════════

@tool
def kpis_globaux() -> str:
    """KPIs globaux banque : clients, comptes, réclamations, chèques, recovery.
    Appeler en premier pour tout rapport ou dashboard global."""
    return json.dumps({
        "total_clients":              count("customers"),
        "total_accounts":             count("accounts"),
        "total_reclamations":         count("reclamations"),
        "total_cheques":              count("cheques"),
        "total_recovery_loans":       count("recovery_loans"),
        "reclamations_ouvertes":      count("reclamations", {
            "status": {"$in": ["en cours","ouverte","ouvert","open"]}}),
        "compte_recouvrement_actifs": count("recovery_loans", {"loan_paid_back": False}),
    })


# ═══════════════════════════════════════════════════════════════
# RÉCLAMATIONS — acceptent cin + période
# ═══════════════════════════════════════════════════════════════

@tool
def reclamations_kpis(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """KPIs réclamations : total, ouvertes, traitées.
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "filtre": _period_label(cin, date_debut, date_fin)})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    match = _build_match(customer_id, d1, d2)
    pipeline = ([{"$match": match}] if match else []) + [
        {"$group": {
            "_id":     None,
            "total":   {"$sum": 1},
            "ouvertes":{"$sum": {"$cond": [{"$in": ["$status",["en cours","ouverte","ouvert","open"]]},1,0]}},
            "traitees":{"$sum": {"$cond": [{"$in": ["$status",["traité","traite","closed"]]},1,0]}}
        }}
    ]
    r = aggregate("reclamations", pipeline)
    result = r[0] if r else {"total": 0, "ouvertes": 0, "traitees": 0}
    result.pop("_id", None)
    result["filtre"] = _period_label(cin, date_debut, date_fin)
    # Nom du client si CIN
    if customer_id:
        profil = fetch("customers", filtre={"_id": ObjectId(customer_id)},
                       projection={"personal_info.nom":1,"personal_info.prenom":1}, limit=1)
        if profil:
            pi = profil[0].get("personal_info", {})
            result["client_nom"] = f"{pi.get('prenom','')} {pi.get('nom','')}".strip()
    return json.dumps(result)


@tool
def reclamations_par_statut(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """Répartition des réclamations par statut.
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    match = _build_match(customer_id, d1, d2)
    pipeline = ([{"$match": match}] if match else []) + [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    return json.dumps({"data": aggregate("reclamations", pipeline),
                        "filtre": _period_label(cin, date_debut, date_fin)})


@tool
def reclamations_par_objet(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """Top 10 motifs de réclamations.
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    match = _build_match(customer_id, d1, d2)
    pipeline = ([{"$match": match}] if match else []) + [
        {"$group": {"_id": "$objet", "count": {"$sum": 1}}},
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"count": -1}}, {"$limit": 10}
    ]
    return json.dumps({"data": aggregate("reclamations", pipeline),
                        "filtre": _period_label(cin, date_debut, date_fin)})


@tool
def reclamations_serie_temporelle(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """Évolution temporelle des réclamations (mensuelle ou journalière).
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    fmt = "%Y-%m-%d" if (d1 and d2 and (d2-d1).days < 60) else "%Y-%m"
    match = _build_match(customer_id, d1, d2)
    pipeline = ([{"$match": match}] if match else []) + [
        {"$group": {"_id": {"$dateToString": {"format": fmt, "date": {"$toDate": "$date"}}}, "count": {"$sum": 1}}},
        {"$match": {"_id": {"$ne": None}}}, {"$sort": {"_id": 1}}
    ]
    return json.dumps({"data": aggregate("reclamations", pipeline),
                        "filtre": _period_label(cin, date_debut, date_fin),
                        "format": fmt})


@tool
def delai_moyen_resolution(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """Délai moyen de résolution en heures (SLA).
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable"})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    base_filter = {"status": {"$in": ["traité","traite","closed"]}, "date_rep": {"$ne": None}}
    if customer_id:
        base_filter["customer_id"] = customer_id
    dm = _build_date_match(d1, d2)
    base_filter.update(dm)
    pipeline = [
        {"$match": base_filter},
        {"$addFields": {"duree_ms": {"$subtract": [{"$toDate": "$date_rep"}, {"$toDate": "$date"}]}}},
        {"$match": {"duree_ms": {"$ne": None}}},
        {"$group": {"_id": None, "duree_moy_ms": {"$avg": "$duree_ms"}, "count": {"$sum": 1}}},
        {"$addFields": {"duree_moy_heures": {"$divide": ["$duree_moy_ms", 3600000]}}}
    ]
    r = aggregate("reclamations", pipeline)
    result = r[0] if r else {"duree_moy_heures": None, "count": 0}
    result.pop("_id", None)
    result["filtre"] = _period_label(cin, date_debut, date_fin)
    return json.dumps(result)


@tool
def reclamations_delai_par_objet(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """Délai moyen de résolution par motif.
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    base_filter = {"date_rep": {"$ne": None}}
    if customer_id:
        base_filter["customer_id"] = customer_id
    dm = _build_date_match(d1, d2)
    base_filter.update(dm)
    pipeline = [
        {"$match": base_filter},
        {"$addFields": {"duree_h": {"$divide": [{"$subtract": [{"$toDate": "$date_rep"},{"$toDate": "$date"}]}, 3600000]}}},
        {"$group": {"_id": "$objet", "delai_moyen": {"$avg": "$duree_h"}, "count": {"$sum": 1}}},
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"delai_moyen": -1}}, {"$limit": 10}
    ]
    return json.dumps({"data": aggregate("reclamations", pipeline),
                        "filtre": _period_label(cin, date_debut, date_fin)})


# ═══════════════════════════════════════════════════════════════
# TRANSACTIONS — acceptent cin + période
# ═══════════════════════════════════════════════════════════════

def _txn_base_match(customer_id, d1, d2):
    """Construit le match pour les transactions (via account_numbers si client)."""
    base = {}
    if customer_id:
        nums = _get_account_numbers(customer_id)
        if nums:
            base["account_number"] = {"$in": nums}
    dm = _build_date_match(d1, d2)
    base.update(dm)
    return base


@tool
def transactions_kpis(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """KPIs transactions : total, volume, montant moyen, max.
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable"})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    base = _txn_base_match(customer_id, d1, d2)
    pipeline = ([{"$match": base}] if base else []) + [
        {"$group": {"_id": None, "total": {"$sum": 1},
                    "montant": {"$sum": "$amount"}, "moy": {"$avg": "$amount"},
                    "max": {"$max": "$amount"}}}
    ]
    r = aggregate("bank_transactions", pipeline)
    result = r[0] if r else {"total": 0, "montant": 0, "moy": 0, "max": 0}
    result.pop("_id", None)
    result["filtre"] = _period_label(cin, date_debut, date_fin)
    if customer_id:
        profil = fetch("customers", filtre={"_id": ObjectId(customer_id)},
                       projection={"personal_info.nom":1,"personal_info.prenom":1}, limit=1)
        if profil:
            pi = profil[0].get("personal_info", {})
            result["client_nom"] = f"{pi.get('prenom','')} {pi.get('nom','')}".strip()
    return json.dumps(result)


@tool
def transactions_par_type(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """Volume et montant des transactions par type.
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    base = _txn_base_match(customer_id, d1, d2)
    pipeline = ([{"$match": base}] if base else []) + [
        {"$group": {"_id": "$type", "nombre": {"$sum": 1},
                    "montant_total": {"$sum": "$amount"}, "montant_moyen": {"$avg": "$amount"}}},
        {"$match": {"_id": {"$ne": None}}}, {"$sort": {"montant_total": -1}}
    ]
    return json.dumps({"data": aggregate("bank_transactions", pipeline),
                        "filtre": _period_label(cin, date_debut, date_fin)})


@tool
def transactions_serie_temporelle(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """Évolution mensuelle/journalière des transactions.
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    fmt = "%Y-%m-%d" if (d1 and d2 and (d2-d1).days < 60) else "%Y-%m"
    base = _txn_base_match(customer_id, d1, d2)
    pipeline = ([{"$match": base}] if base else []) + [
        {"$group": {"_id": {"$dateToString": {"format": fmt, "date": {"$toDate": "$date"}}},
                    "nb_transactions": {"$sum": 1}, "montant_total": {"$sum": "$amount"}}},
        {"$match": {"_id": {"$ne": None}}}, {"$sort": {"_id": 1}}
    ]
    return json.dumps({"data": aggregate("bank_transactions", pipeline),
                        "filtre": _period_label(cin, date_debut, date_fin), "format": fmt})


@tool
def transactions_par_heure(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """Distribution horaire des transactions.
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    base = _txn_base_match(customer_id, d1, d2)
    pipeline = ([{"$match": base}] if base else []) + [
        {"$group": {"_id": {"$hour": {"$toDate": "$date"}}, "count": {"$sum": 1}, "total": {"$sum": "$amount"}}},
        {"$match": {"_id": {"$ne": None}}}, {"$sort": {"_id": 1}}
    ]
    return json.dumps({"data": aggregate("bank_transactions", pipeline),
                        "filtre": _period_label(cin, date_debut, date_fin)})


@tool
def transactions_top_montants(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """Top 10 transactions par montant (alertes anomalies).
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    base = _txn_base_match(customer_id, d1, d2)
    pipeline = ([{"$match": base}] if base else []) + [
        {"$sort": {"amount": -1}}, {"$limit": 10}
    ]
    return json.dumps({"data": aggregate("bank_transactions", pipeline),
                        "filtre": _period_label(cin, date_debut, date_fin)})


@tool
def comparaison_deux_periodes(debut_p1: str = "", fin_p1: str = "",
                               debut_p2: str = "", fin_p2: str = "") -> str:
    """Compare les transactions entre deux périodes.
    Args: debut_p1, fin_p1, debut_p2, fin_p2 (YYYY-MM-DD)"""
    if isinstance(debut_p1, str) and debut_p1.strip().startswith("{"):
        try:
            d = json.loads(debut_p1)
            debut_p1 = d.get("debut_p1",""); fin_p1 = d.get("fin_p1","")
            debut_p2 = d.get("debut_p2",""); fin_p2 = d.get("fin_p2","")
        except Exception: pass
    if isinstance(debut_p1, dict):
        fin_p1 = debut_p1.get("fin_p1",""); debut_p2 = debut_p1.get("debut_p2","")
        fin_p2 = debut_p1.get("fin_p2",""); debut_p1 = debut_p1.get("debut_p1","")

    def _stats(d1s, d2s):
        d1, d2 = _parse_dates(d1s or "", d2s or "")
        if not d1 or not d2: return []
        return aggregate("bank_transactions", [
            {"$match": {"date": {"$gte": d1, "$lte": d2 + timedelta(days=1)}}},
            {"$group": {"_id": "$type", "count": {"$sum":1}, "total": {"$sum":"$amount"}}},
            {"$sort": {"total": -1}}])

    return json.dumps({
        "periode_1": {"label": f"{debut_p1}→{fin_p1}", "data": _stats(debut_p1, fin_p1)},
        "periode_2": {"label": f"{debut_p2}→{fin_p2}", "data": _stats(debut_p2, fin_p2)},
    }, default=str)


# ═══════════════════════════════════════════════════════════════
# CRÉDITS — acceptent cin + période
# ═══════════════════════════════════════════════════════════════

def _loans_pipeline_base(customer_id, d1, d2):
    """Pipeline de base pour les agrégations sur loans."""
    pipeline = []
    if customer_id:
        pipeline.append({"$match": {"_id": ObjectId(customer_id)}})
    pipeline.append({"$unwind": "$loans"})
    if d1 and d2:
        pipeline.append({"$match": {
            "loans.date_debut_loan": {"$gte": d1, "$lte": d2 + timedelta(days=1)}
        }})
    return pipeline


@tool
def loans_stats_globales(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """KPIs globaux du portefeuille de prêts.
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable"})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    pipeline = _loans_pipeline_base(customer_id, d1, d2) + [
        {"$group": {"_id": None,
                    "total_loans":   {"$sum": 1},
                    "montant_total": {"$sum": "$loans.loan_amount"},
                    "montant_moyen": {"$avg": "$loans.loan_amount"},
                    "taux_moyen":    {"$avg": "$loans.loan_interest_rate"},
                    "rembourses":    {"$sum": {"$cond": ["$loans.loan_paid_back",1,0]}}}},
        {"$addFields": {"taux_remboursement_global": {"$cond": [
            {"$gt": ["$total_loans",0]},
            {"$multiply": [{"$divide": ["$rembourses","$total_loans"]},100]},
            0]}}}
    ]
    r = aggregate("customers", pipeline)
    result = r[0] if r else {}
    result.pop("_id", None)
    result["filtre"] = _period_label(cin, date_debut, date_fin)
    return json.dumps(result)


@tool
def loans_par_grade(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """Distribution des prêts par grade avec taux de remboursement.
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    pipeline = _loans_pipeline_base(customer_id, d1, d2) + [
        {"$group": {"_id": "$loans.grade_subgrade",
                    "total":         {"$sum": 1},
                    "montant_total": {"$sum": "$loans.loan_amount"},
                    "taux_moyen":    {"$avg": "$loans.loan_interest_rate"},
                    "rembourses":    {"$sum": {"$cond": ["$loans.loan_paid_back",1,0]}}}},
        {"$addFields": {"taux_remboursement_pct": {"$cond": [
            {"$gt":["$total",0]},
            {"$multiply":[{"$divide":["$rembourses","$total"]},100]},
            0]}}},
        {"$match": {"_id": {"$ne": None}}}, {"$sort": {"_id": 1}}
    ]
    return json.dumps({"data": aggregate("customers", pipeline),
                        "filtre": _period_label(cin, date_debut, date_fin)})


@tool
def loans_par_objet(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """Répartition des prêts par objet/purpose.
    Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    pipeline = _loans_pipeline_base(customer_id, d1, d2) + [
        {"$group": {"_id": "$loans.loan_purpose",
                    "count": {"$sum":1}, "montant_total": {"$sum":"$loans.loan_amount"}}},
        {"$match": {"_id": {"$ne": None}}}, {"$sort": {"montant_total": -1}}
    ]
    return json.dumps({"data": aggregate("customers", pipeline),
                        "filtre": _period_label(cin, date_debut, date_fin)})


# @tool
# def loans_taux_interet_distribution(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
#     """Distribution des taux d'intérêt par tranches.
#     Args: cin (optionnel), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
#     cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
#     customer_id = _cin_to_customer_id(cin) if cin else None
#     if cin and not customer_id:
#         return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
#     d1, d2 = _parse_dates(date_debut or "", date_fin or "")
#     pipeline = _loans_pipeline_base(customer_id, d1, d2) + [
#         {"$match": {"loans.loan_interest_rate": {"$exists":True,"$ne":None}}},
#         {"$bucket": {"groupBy":"$loans.loan_interest_rate",
#                      "boundaries":[0,5,8,11,14,17,20,30],"default":"autre",
#                      "output":{"count":{"$sum":1},"montant_moyen":{"$avg":"$loans.loan_amount"}}}}
#     ]
#     raw = aggregate("customers", pipeline)
#     # Formater les labels des tranches
#     result = []
#     for item in raw:
#         item_copy = dict(item)
#         if item_copy.get("_id") != "autre":
#             item_copy["_id"] = f"{item_copy['_id']}%"
#         result.append(item_copy)
#     return json.dumps({"data": result, "filtre": _period_label(cin, date_debut, date_fin)})


@tool
def loans_liste_client(cin: str = "", date_debut: str = "", date_fin: str = "") -> str:
    """Liste détaillée des prêts (surtout utile pour un client spécifique).
    Args: cin (obligatoire pour usage client), date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    cin, date_debut, date_fin = _extract_args(cin, date_debut, date_fin)
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
    d1, d2 = _parse_dates(date_debut or "", date_fin or "")
    pipeline = _loans_pipeline_base(customer_id, d1, d2) + [
        {"$project": {"_id":0,"montant":"$loans.loan_amount","loan_purpose":"$loans.loan_purpose",
                      "taux":"$loans.loan_interest_rate","loan_term":"$loans.loan_term",
                      "grade_subgrade":"$loans.grade_subgrade","loan_paid_back":"$loans.loan_paid_back",
                      "date_debut":"$loans.date_debut_loan","date_fin":"$loans.date_fin_loan"}}
    ]
    return json.dumps({"data": aggregate("customers", pipeline),
                        "filtre": _period_label(cin, date_debut, date_fin)}, default=str)


@tool
def scores_credit_distribution() -> str:
    """Histogramme des scores crédit par tranche (300→1000). Global uniquement."""
    return json.dumps(aggregate("customers", [
        {"$match": {"credit_profile.credit_score": {"$exists":True,"$ne":None}}},
        {"$bucket": {"groupBy":"$credit_profile.credit_score",
                     "boundaries":[300,450,580,670,740,800,1000],"default":"non_renseigne",
                     "output":{"count":{"$sum":1},"score_moyen":{"$avg":"$credit_profile.credit_score"}}}}
    ]))


@tool
def score_moyen_par_region() -> str:
    """Score crédit moyen par région géographique."""
    return json.dumps(aggregate("customers", [
        {"$match": {"credit_profile.credit_score":{"$exists":True}}},
        {"$group": {"_id":"$personal_info.region",
                    "score_moyen":{"$avg":"$credit_profile.credit_score"},"count":{"$sum":1}}},
        {"$match": {"_id":{"$ne":None}}}, {"$sort": {"score_moyen":-1}}
    ]))


@tool
def clients_en_defaut(limit: str = "20") -> str:
    """Clients avec historique de défaut de paiement."""
    try:
        if isinstance(limit, str) and limit.startswith("{"): limit = json.loads(limit).get("limit",20)
        limit = int(limit)
    except Exception: limit = 20
    return json.dumps(fetch("customers",
        filtre={"credit_profile.delinquency_history":True},
        projection={"personal_info.nom":1,"personal_info.prenom":1,"personal_info.region":1,"credit_profile":1},
        sort={"credit_profile.num_of_delinquencies":-1}, limit=limit))


# ═══════════════════════════════════════════════════════════════
# COMPTES — acceptent cin
# ═══════════════════════════════════════════════════════════════

@tool
def accounts_par_type(cin: str = "") -> str:
    """Solde total et moyen par type de compte.
    Args: cin (optionnel — filtre sur le client si fourni)"""
    cin = _clean(cin) if isinstance(cin, str) else None
    if isinstance(cin, str) and cin.startswith("{"):
        try: cin = _clean(json.loads(cin).get("cin",""))
        except Exception: cin = None
    customer_id = _cin_to_customer_id(cin) if cin else None
    if cin and not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable"})
    match = {"customer_id": customer_id} if customer_id else {}
    pipeline = ([{"$match": match}] if match else []) + [
        {"$group": {"_id":"$type","count":{"$sum":1},
                    "solde_total":{"$sum":"$balance"},
                    "solde_moyen":{"$avg":"$balance"},
                    "solde_max":  {"$max":"$balance"}}},
        {"$match": {"_id":{"$ne":None}}}, {"$sort": {"solde_total":-1}}
    ]
    return json.dumps(aggregate("accounts", pipeline))


@tool
def accounts_par_statut(cin: str = "") -> str:
    """Répartition des comptes par statut.
    Args: cin (optionnel)"""
    cin = _clean(cin) if isinstance(cin, str) else None
    if isinstance(cin, str) and cin.startswith("{"):
        try: cin = _clean(json.loads(cin).get("cin",""))
        except Exception: cin = None
    customer_id = _cin_to_customer_id(cin) if cin else None
    match = {"customer_id": customer_id} if customer_id else {}
    pipeline = ([{"$match": match}] if match else []) + [
        {"$group": {"_id":"$status","count":{"$sum":1}}}, {"$sort":{"count":-1}}
    ]
    return json.dumps(aggregate("accounts", pipeline))


@tool
def solde_total_banque() -> str:
    """Solde total agrégé de tous les comptes."""
    r = aggregate("accounts", [
        {"$group": {"_id":None,"solde_total":{"$sum":"$balance"},
                    "solde_moyen":{"$avg":"$balance"},"count":{"$sum":1}}}
    ])
    return json.dumps(r[0] if r else {"solde_total":0,"solde_moyen":0,"count":0})


@tool
def accounts_du_client_detail(cin: str = "") -> str:
    """Liste détaillée des comptes d'un client par CIN.
    Args: cin (obligatoire)"""
    cin = _clean(cin) if isinstance(cin, str) else None
    if isinstance(cin, str) and cin.startswith("{"):
        try: cin = _clean(json.loads(cin).get("cin",""))
        except Exception: cin = None
    customer_id = _cin_to_customer_id(cin) if cin else None
    if not customer_id:
        return json.dumps({"erreur": f"Client CIN '{cin}' introuvable", "data": []})
    r = aggregate("accounts", [
        {"$match":{"customer_id":customer_id}}, {"$sort":{"balance":-1}},
        {"$project":{"_id":0,"account_number":1,"type":1,"balance":1,"date_creation":1,"status":1}}
    ])
    return json.dumps({"data": r, "filtre": f"CIN {cin}"}, default=str)


# ═══════════════════════════════════════════════════════════════
# CHÈQUES & RECOVERY
# ═══════════════════════════════════════════════════════════════

@tool
def cheques_par_statut(date_debut: str = "", date_fin: str = "") -> str:
    """Répartition des chèques par statut.
    Args: date_debut YYYY-MM-DD (optionnel), date_fin YYYY-MM-DD (optionnel)"""
    if isinstance(date_debut, str) and date_debut.strip().startswith("{"):
        try:
            d = json.loads(date_debut)
            date_debut = d.get("date_debut",""); date_fin = d.get("date_fin","")
        except Exception: pass
    d1, d2 = _parse_dates(_clean(date_debut) or "", _clean(date_fin) or "")
    dm = _build_date_match(d1, d2, "date_emission")
    pipeline = ([{"$match": dm}] if dm else []) + [
        {"$group": {"_id":"$status","count":{"$sum":1}}}, {"$sort":{"count":-1}}
    ]
    return json.dumps(aggregate("cheques", pipeline))


@tool
def recovery_par_statut() -> str:
    """Répartition des prêts en recouvrement par statut."""
    return json.dumps(aggregate("recovery_loans", [
        {"$group": {"_id":"$status","count":{"$sum":1}}}, {"$sort":{"count":-1}}
    ]))


@tool
def recovery_montants() -> str:
    """Montants en recouvrement et statistiques."""
    r = aggregate("recovery_loans", [
        {"$group": {"_id":None,"montant_total":{"$sum":"$loan_monthly_part"},
                    "montant_moyen":{"$avg":"$loan_monthly_part"},"count":{"$sum":1},
                    "non_rembourses":{"$sum":{"$cond":[{"$eq":["$loan_paid_back",False]},1,0]}}}}
    ])
    result = r[0] if r else {}
    result.pop("_id", None)
    return json.dumps(result)


# ═══════════════════════════════════════════════════════════════
# CLIENTS
# ═══════════════════════════════════════════════════════════════

@tool
def clients_par_region() -> str:
    """Répartition des clients par région tunisienne."""
    return json.dumps(aggregate("customers", [
        {"$group": {"_id":"$personal_info.region","count":{"$sum":1}}},
        {"$match":{"_id":{"$ne":None}}}, {"$sort":{"count":-1}}
    ]))


@tool
def clients_par_genre() -> str:
    """Répartition H/F des clients."""
    return json.dumps(aggregate("customers", [
        {"$group": {"_id":"$personal_info.genre","count":{"$sum":1}}},
        {"$match":{"_id":{"$ne":None}}}
    ]))


@tool
def revenu_moyen_par_region() -> str:
    """Revenu annuel moyen des clients par région."""
    return json.dumps(aggregate("customers", [
        {"$group": {"_id":"$personal_info.region",
                    "revenu_moyen":{"$avg":"$employment.annual_income"},"count":{"$sum":1}}},
        {"$match":{"_id":{"$ne":None}}}, {"$sort":{"revenu_moyen":-1}}
    ]))


@tool
def correlation_score_revenu() -> str:
    """Corrélation score crédit / revenu par tranche."""
    return json.dumps(aggregate("customers", [
        {"$match": {"credit_profile.credit_score":{"$exists":True,"$ne":None},
                    "employment.annual_income":{"$exists":True,"$ne":None}}},
        {"$bucket": {"groupBy":"$employment.annual_income",
                     "boundaries":[0,20000,40000,60000,80000,100000,150000,500000],
                     "default":"autre",
                     "output":{"count":{"$sum":1},"score_moyen":{"$avg":"$credit_profile.credit_score"},
                               "revenu_moyen":{"$avg":"$employment.annual_income"}}}}
    ]))


# ═══════════════════════════════════════════════════════════════
# CLIENT COMPLET
# ═══════════════════════════════════════════════════════════════

@tool
def analyse_complete_client(cin: str) -> str:
    """Analyse complète d'un client par CIN.A utiliser seulment pour une analyse détaillée d'un client spécifique .
    Args: cin — CIN du client (obligatoire)"""
    # Normaliser l'input
    if isinstance(cin, dict): cin = cin.get("cin","")
    if isinstance(cin, str) and cin.strip().startswith("{"):
        try: cin = json.loads(cin).get("cin","")
        except Exception: pass
    cin = _clean(cin)
    if not cin: return json.dumps({"erreur": "CIN obligatoire"})

    customer_id = _cin_to_customer_id(cin)
    if not customer_id: return json.dumps({"erreur": f"Client CIN '{cin}' introuvable"})

    profil = fetch("customers", filtre={"_id": ObjectId(customer_id)},
                   projection={"personal_info":1,"employment":1,"credit_profile":1}, limit=1)
    profil = profil[0] if profil else {}

    loans = aggregate("customers", [
        {"$match":{"_id":ObjectId(customer_id)}}, {"$unwind":"$loans"},
        {"$project":{"_id":0,"montant":"$loans.loan_amount","loan_purpose":"$loans.loan_purpose",
                     "taux":"$loans.loan_interest_rate","loan_term":"$loans.loan_term",
                     "grade_subgrade":"$loans.grade_subgrade","loan_paid_back":"$loans.loan_paid_back",
                     "date_debut":"$loans.date_debut_loan","date_fin":"$loans.date_fin_loan"}}
    ])
    reclamations = fetch("reclamations", filtre={"customer_id":customer_id}, sort={"date":-1})
    accounts = aggregate("accounts", [
        {"$match":{"customer_id":customer_id}}, {"$sort":{"balance":-1}},
        {"$project":{"_id":0,"account_number":1,"type":1,"balance":1,"date_creation":1,"status":1}}
    ])
    nums = [a["account_number"] for a in accounts if a.get("account_number")]
    transactions = aggregate("bank_transactions", [
        {"$match":{"account_number":{"$in":nums}}}, {"$sort":{"date":-1}},
        {"$group":{"_id":"$account_number","nombre_transactions":{"$sum":1},
                   "montant_total":{"$sum":"$amount"},
                   "dernieres_transactions":{"$push":{"date":"$date","label":"$desc","amount":"$amount","type":"$type"}}}},
        {"$project":{"_id":0,"account_number":"$_id","nombre_transactions":1,"montant_total":1,
                     "dernieres_transactions":{"$slice":["$dernieres_transactions",5]}}}
    ])
    return json.dumps({"cin":cin,"customer_id":customer_id,"profil":profil,
                        "loans":loans,"reclamations":reclamations,
                        "accounts":accounts,"transactions":transactions}, default=str)


# ═══════════════════════════════════════════════════════════════
# RAPPORT COMPLET
# ═══════════════════════════════════════════════════════════════

@tool
def rapport_complet_data() -> str:
    """Toutes les données agrégées pour rapport global hebdomadaire. Un seul appel."""
    import json as _j
    return json.dumps({
        "kpis":                _j.loads(kpis_globaux.invoke({})),
        "clients_region":      _j.loads(clients_par_region.invoke({})),
        "clients_genre":       _j.loads(clients_par_genre.invoke({})),
        "transactions_type":   _j.loads(transactions_par_type.invoke({})),
        "transactions_serie":  _j.loads(transactions_serie_temporelle.invoke({})),
        "loans_grade":         _j.loads(loans_par_grade.invoke({})),
        "loans_objet":         _j.loads(loans_par_objet.invoke({})),
        "loans_stats":         _j.loads(loans_stats_globales.invoke({})),
        "scores":              _j.loads(scores_credit_distribution.invoke({})),
        "score_region":        _j.loads(score_moyen_par_region.invoke({})),
        "reclamations_statut": _j.loads(reclamations_par_statut.invoke({})),
        "reclamations_objet":  _j.loads(reclamations_par_objet.invoke({})),
        "reclamations_serie":  _j.loads(reclamations_serie_temporelle.invoke({})),
        "delai_resolution":    _j.loads(delai_moyen_resolution.invoke({})),
        "accounts_type":       _j.loads(accounts_par_type.invoke({})),
        "solde_total":         _j.loads(solde_total_banque.invoke({})),
        "recovery":            _j.loads(recovery_montants.invoke({})),
        "cheques_statut":      _j.loads(cheques_par_statut.invoke({})),
    })


# ═══════════════════════════════════════════════════════════════
# ALL_TOOLS
# ═══════════════════════════════════════════════════════════════
ALL_TOOLS = [
    kpis_globaux,
    # Réclamations
    reclamations_kpis, reclamations_par_statut, reclamations_par_objet,
    reclamations_serie_temporelle, delai_moyen_resolution, reclamations_delai_par_objet,
    # Transactions
    transactions_kpis, transactions_par_type, transactions_serie_temporelle,
    transactions_par_heure, transactions_top_montants, comparaison_deux_periodes,
    # Crédits
    loans_stats_globales, loans_par_grade, loans_par_objet,
     loans_liste_client,
    scores_credit_distribution, score_moyen_par_region, clients_en_defaut,
    # Comptes
    accounts_par_type, accounts_par_statut, solde_total_banque, accounts_du_client_detail,
    cheques_par_statut, recovery_par_statut, recovery_montants,
    # Clients
    clients_par_region, clients_par_genre, revenu_moyen_par_region, correlation_score_revenu,
    # Rapport & client complet
    rapport_complet_data, analyse_complete_client,
]
