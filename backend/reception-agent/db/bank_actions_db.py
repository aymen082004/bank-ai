from __future__ import annotations

import datetime as _dt
import os
import re
import json
from typing import Any, Dict, Optional

from pymongo import MongoClient
try:
    from . import rag_engine
except ImportError:
    import rag_engine
from tavily import TavilyClient
from dotenv import load_dotenv

# Charger .env pour les clés API (Tavily, etc.)
load_dotenv()


MONGO_URI = os.environ.get(
    "BANK_MONGO_URI",
    "mongodb+srv://alexhunter2020111_db_user:HUrHSfVkpCL1CrAb@cluster0.0rav9u6.mongodb.net/?appName=Cluster0",
)
MONGO_DB_NAME = os.environ.get("BANK_MONGO_DB", "bank_ai")
MONGO_COLLECTION = os.environ.get("BANK_MONGO_CUSTOMERS_COLLECTION", "customers")

_client = MongoClient(MONGO_URI)
_db = _client[MONGO_DB_NAME]
_customers = _db[MONGO_COLLECTION]
_accounts = _db["accounts"]
_cards = _db["bank_cards"]
_transactions = _db["bank_transactions"]
_params = _db["bank_params"]

# Initialize Tavily client if key is present
_tavily = None
if os.environ.get("TAVILY_API_KEY"):
    _tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

import sys
import re

def search_faiss(query: str) -> str:
    """Recherche dans la documentation interne BH Bank via FAISS. Passe au web automatiquement si rien n'est trouvé."""
    print(f"[DB] search_faiss call: query='{query}'", file=sys.stderr)
    
    # Intercepteur : Si la question contient une année 2024 ou plus, on by-passe FAISS 
    # car les archives internes datent parfois de 1993 ("Abou Hafs Amor Najai").
    if re.search(r'202[4-9]|20[3-9]\d', query):
        print(f"[DB] Année récente détectée dans la question. Basculement Web immédiat.", file=sys.stderr)
        web_res = search_web(query)
        return f"INFORMATION_NON_TROUVEE_EN_LOCAL. La base documentaire interne est trop ancienne pour cette date. Voici l'actualité selon le web :\n{web_res}"
        
    context = rag_engine.retrieve_context(query, top_k=8)
    if not context:
        print(f"[DB] FAISS returned empty, attempting web search fallback for: '{query}'", file=sys.stderr)
        web_res = search_web(query)
        return f"INFORMATION_NON_TROUVEE_EN_LOCAL. La documentation interne ne contient pas cette information.\nCependant, une recherche Web a retourné les résultats suivants:\n{web_res}"
    return context

def search_web(query: str) -> str:
    """Recherche sur internet via Tavily (si nécessaire)."""
    print(f"[DB] search_web call: query='{query}'", file=sys.stderr)
    if not _tavily:
        return "Recherche web désactivée (Clé API manquante)."
    try:
        search_query = f"BH Bank Tunisie {query}"
        search_result = _tavily.search(query=search_query, search_depth="basic", max_results=3)
        results = []
        for r in search_result.get("results", []):
            results.append(f"Source: {r['url']}\nContenu: {r['content']}")
        return "\n\n".join(results) if results else "Aucun résultat web trouvé."
    except Exception as e:
        return f"Erreur lors de la recherche web: {str(e)}"


def _now_iso() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")

def _safe_float(val: Any) -> float:
    if val is None: return 0.0
    if isinstance(val, (int, float)): return float(val)
    # Extract only valid numeric characters (digits and dot), removing "DT", " DT", etc.
    s = str(val).upper().replace(",", ".").replace("DT", "").replace(" ", "").strip()
    match = re.search(r"[-+]?\d*\.\d+|\d+", s)
    if match:
        try:
            return float(match.group(0))
        except:
            return 0.0
    return 0.0


def extract_card_id(question: str) -> Optional[str]:
    m = re.search(r"(CARD[-]?\d+|[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4})", question, re.IGNORECASE)
    return m.group(1).upper() if m else None


def extract_account_id(question: str) -> Optional[str]:
    # Match UUID-like or A001-like patterns
    m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|A\d+)", question, re.IGNORECASE)
    return m.group(1) if m else None


def _resolve_customer_doc(identifier: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Search for a customer by ID (OID), name, or CIN.
    """
    if not identifier:
        return None
    print(f"[DEBUG DB] _resolve_customer_doc identifier='{identifier}'")
    identifier = identifier.strip()
    # Nettoyage si 'de ' ou 'pour ' est resté au début
    identifier = re.sub(r"^(de|pour|le client)\s+", "", identifier, flags=re.IGNORECASE)
    
    # 1. Try as ObjectId directly if valid
    if identifier and len(identifier) == 24:
        try:
            from bson import ObjectId
            doc = _customers.find_one({"_id": ObjectId(identifier)})
            if doc: return doc
        except: pass
        
    # 2. Try by Name (regex)
    doc = _customers.find_one({
        "$or": [
            {"personal_info.nom": {"$regex": f"^{identifier}$", "$options": "i"}},
            {"personal_info.prenom": {"$regex": f"^{identifier}$", "$options": "i"}}
        ]
    })
    if doc: return doc

    # 3. Try variations for names with spaces...
    # (keeping the existing words split logic)
    words = identifier.split() if identifier else []
    if len(words) >= 2:
        query = {
            "$or": [
                {"personal_info.nom": {"$regex": words[0], "$options": "i"}, "personal_info.prenom": {"$regex": " ".join(words[1:]), "$options": "i"}},
                {"personal_info.prenom": {"$regex": words[0], "$options": "i"}, "personal_info.nom": {"$regex": " ".join(words[1:]), "$options": "i"}},
                {"personal_info.nom": {"$regex": words[-1], "$options": "i"}, "personal_info.prenom": {"$regex": " ".join(words[:-1]), "$options": "i"}},
                {"personal_info.prenom": {"$regex": words[-1], "$options": "i"}, "personal_info.nom": {"$regex": " ".join(words[:-1]), "$options": "i"}},
                {"personal_info.nom": {"$regex": f"^{identifier}$", "$options": "i"}},
                {"personal_info.prenom": {"$regex": f"^{identifier}$", "$options": "i"}}
            ]
        }
        doc = _customers.find_one(query)
        if doc: return doc

    # 4. Try by Account Number
    print(f"[DEBUG DB] Checking account_number='{identifier}'")
    acc = _accounts.find_one({"account_number": identifier})
    if acc:
        print(f"[DEBUG DB] Account found! customer_id='{acc['customer_id']}'")
        from bson import ObjectId
        try:
            cust_id_obj = ObjectId(acc["customer_id"]) if isinstance(acc["customer_id"], str) else acc["customer_id"]
            doc = _customers.find_one({"_id": cust_id_obj})
            if doc: 
                print(f"[DEBUG DB] Customer resolved: {doc['personal_info'].get('nom')}")
                return doc
        except Exception as e:
            print(f"[DEBUG DB] Error resolving customer: {e}")

    # 5. Try by CIN
    doc = _customers.find_one({"personal_info.cin": identifier})
    if doc: return doc

    print(f"[DEBUG DB] No customer found for '{identifier}'")
    return None


def open_account(customer_id: Optional[str], account_type: str = "courant", initial_deposit: float = 0.0) -> Dict[str, Any]:
    print(f"[DB] open_account call: customer={customer_id}, type={account_type}, deposit={initial_deposit}")
    doc = _resolve_customer_doc(customer_id)
    if not doc:
        return {"status": "ERROR", "error": f"Le client '{customer_id}' n'existe pas. Veuillez d'abord le créer à l'Étape 1."}

    import uuid
    account_number = str(uuid.uuid4())
    
    safe_deposit = _safe_float(initial_deposit)
    
    new_account = {
        "customer_id": str(doc["_id"]),
        "account_number": account_number,
        "type": account_type.lower(),
        "balance": safe_deposit,
        "date_creation": _dt.datetime.now(),
        "status": "active"
    }
    _accounts.insert_one(new_account)

    # Log action
    tx_entry = {
        "account_number": account_number,
        "date": _dt.datetime.now(),
        "amount": safe_deposit,
        "type": "CREDIT",
        "desc": "Dépôt Initial (Ouverture de compte)"
    }
    _transactions.insert_one(tx_entry)
    
    _customers.update_one({"_id": doc["_id"]}, {"$push": {"transactions": {
        "type": "OPEN_ACCOUNT",
        "account_number": account_number,
        "amount": safe_deposit,
        "created_at": _now_iso()
    }}})

    # Display Name standardisé: Prénom Nom (Capitalisé)
    prenom = doc['personal_info'].get('prenom') or ""
    nom = doc['personal_info'].get('nom') or ""
    full_name = f"{prenom} {nom}".strip()
    display_name = " ".join([w.capitalize() for w in full_name.split() if w.lower() != "none"])

    return {
        "status": "CREATED",
        "customer": display_name,
        "account_number": account_number,
        "type": account_type,
        "balance": initial_deposit
    }


def get_balance(customer_id: Optional[str], account_id: Optional[str] = None) -> Dict[str, Any]:
    doc = _resolve_customer_doc(customer_id)
    if not doc:
        return {"status": "ERROR", "error": "Compte introuvable."}

    # Si customer_id ressemble à un numéro de compte (UUID), on restreint la recherche
    is_direct_account = False
    if customer_id and "-" in customer_id and len(customer_id) >= 32:
        # On vérifie si ce compte existe vraiment
        direct_acc = _accounts.find_one({"account_number": customer_id})
        if direct_acc:
            is_direct_account = True
            account_id = customer_id # On force le filtrage par account_id

    query = {"customer_id": str(doc["_id"])}
    if account_id:
        # Search by exact number or suffix
        query["$or"] = [
            {"account_number": account_id},
            {"account_number": {"$regex": f"{account_id}$"}}
        ]
    
    accounts = list(_accounts.find(query))
    if not accounts:
        return {"status": "NOT_FOUND", "message": "Aucun compte trouvé pour ce client.", "customer": doc['personal_info']['nom']}

    results = []
    for acc in accounts:
        results.append({
            "account_number": acc["account_number"],
            "type": acc["type"],
            "balance": acc["balance"],
            "status": acc["status"]
        })

    # Display Name standardisé: Prénom Nom (Capitalisé)
    prenom = doc['personal_info'].get('prenom') or ""
    nom = doc['personal_info'].get('nom') or ""
    full_name = f"{prenom} {nom}".strip()
    display_name = " ".join([w.capitalize() for w in full_name.split() if w.lower() != "none"])

    return {
        "status": "OK",
        "customer": display_name,
        "accounts": results
    }


def _resolve_account_number(identifier: str) -> Optional[str]:
    """Résout un identifiant (Nom, CIN, ou UUID) en numéro de compte valide."""
    if not identifier: return None
    # 1. Si c'est déjà un UUID, on vérifie s'il existe
    acc = _accounts.find_one({"account_number": identifier})
    if acc: return identifier
    # 2. Sinon on résout le client et on prend son premier compte
    doc = _resolve_customer_doc(identifier)
    if doc:
        first_acc = _accounts.find_one({"customer_id": str(doc["_id"])})
        if first_acc: return first_acc["account_number"]
    return None

def generate_statement(account_identifier: str) -> Dict[str, Any]:
    account_number = _resolve_account_number(account_identifier)
    if not account_number:
        return {"status": "ERROR", "error": f"Compte ou client '{account_identifier}' introuvable."}
        
    # Look for transactions in the dedicated collection
    txs = list(_transactions.find({"account_number": account_number}).sort("date", -1).limit(10))
    
    lines = []
    for t in txs:
        # On supporte 'label' ou 'desc' (mon script de populate utilise 'desc')
        label = t.get("desc") or t.get("label") or "Transaction"
        lines.append({
            "date": t.get("date").isoformat()[:10] if isinstance(t.get("date"), _dt.datetime) else str(t.get("date"))[:10],
            "label": label,
            "amount": t.get("amount", 0.0),
            "type": t.get("type", "DEBIT")
        })

    return {
        "account_number": account_number,
        "status": "OK",
        "statement_lines": lines,
        "message": "Données réelles issues de la base de données." if lines else "Aucune transaction trouvée."
    }

def perform_bank_transaction(account_identifier: str, amount: float, transaction_type: str = "DEBIT", description: str = "Transaction") -> Dict[str, Any]:
    """
    Effectue un dépôt (CREDIT) ou un retrait (DEBIT) sur un compte.
    Accepte Nom, CIN ou Numéro de compte.
    """
    account_number = _resolve_account_number(account_identifier)
    if not account_number:
        return {"status": "ERROR", "error": f"Compte ou client '{account_identifier}' introuvable."}
    from bson import ObjectId
    print(f"[DB] perform_bank_transaction: acc={account_number}, amount={amount}, type={transaction_type}")
    
    # 1. Vérifier le compte
    acc = _accounts.find_one({"account_number": account_number})
    if not acc:
        return {"status": "ERROR", "error": f"Compte {account_number} non trouvé."}
    
    amount = abs(_safe_float(amount))
    current_balance = _safe_float(acc.get("balance", 0.0))
    
    # 2. Vérifier les fonds si c'est un retrait
    if transaction_type.upper() == "DEBIT" and current_balance < amount:
        return {
            "status": "ERROR", 
            "error": "Solde insuffisant pour effectuer ce retrait.", 
            "current_balance": current_balance
        }
    
    # 3. Calculer nouveau solde
    if transaction_type.upper() == "CREDIT":
        new_balance = current_balance + amount
    else:
        new_balance = current_balance - amount
        
    # 4. Update DB
    _accounts.update_one({"account_number": account_number}, {"$set": {"balance": new_balance}})
    
    # 5. Log Transaction
    tx_entry = {
        "account_number": account_number,
        "date": _dt.datetime.now(),
        "amount": amount,
        "type": transaction_type.upper(),
        "desc": description or f"{transaction_type.capitalize()} bancaire"
    }
    _transactions.insert_one(tx_entry)
    
    # Log action client
    _customers.update_one({"_id": ObjectId(acc["customer_id"]) if isinstance(acc["customer_id"], str) else acc["customer_id"]}, 
        {"$push": {"transactions": {
            "type": transaction_type.upper(),
            "account_number": account_number,
            "amount": amount,
            "created_at": _now_iso()
        }}})
        
    return {
        "status": "SUCCESS",
        "account_number": account_number,
        "transaction_type": transaction_type.upper(),
        "amount": amount,
        "new_balance": new_balance,
        "message": f"Opération de {transaction_type} effectuée avec succès."
    }


def perform_transfer(from_identifier: str, to_identifier: str, amount: float, description: str = "Virement") -> Dict[str, Any]:
    """
    Effectue un virement entre deux comptes ou clients.
    """
    print(f"[DB] perform_transfer: from={from_identifier}, to={to_identifier}, amount={amount}")
    
    from_account = _resolve_account_number(from_identifier)
    if not from_account:
        return {"status": "ERROR", "error": f"Compte source '{from_identifier}' non trouvé."}
        
    to_account = _resolve_account_number(to_identifier)
    if not to_account:
        return {"status": "ERROR", "error": f"Compte destinataire '{to_identifier}' non trouvé."}
        
    src = _accounts.find_one({"account_number": from_account})
    dst = _accounts.find_one({"account_number": to_account})
    
    amount = abs(_safe_float(amount))
    src_balance = _safe_float(src.get("balance", 0.0))
    
    if src_balance < amount:
        return {"status": "ERROR", "error": "Solde insuffisant pour effectuer ce virement."}
        
    # 3. Mouvements
    new_src_bal = src_balance - amount
    new_dst_bal = _safe_float(dst.get("balance", 0.0)) + amount
    
    _accounts.update_one({"account_number": from_account}, {"$set": {"balance": new_src_bal}})
    _accounts.update_one({"account_number": to_account}, {"$set": {"balance": new_dst_bal}})
    
    # 4. Logs Transactions (DEBIT Source, CREDIT Cible)
    from bson import ObjectId
    
    # Entry for Source
    _transactions.insert_one({
        "account_number": from_account,
        "date": _dt.datetime.now(),
        "amount": amount,
        "type": "DEBIT",
        "desc": f"Virement vers {to_account} - {description}"
    })
    
    # Entry for Cible
    _transactions.insert_one({
        "account_number": to_account,
        "date": _dt.datetime.now(),
        "amount": amount,
        "type": "CREDIT",
        "desc": f"Virement de {from_account} - {description}"
    })
    
    return {
        "status": "SUCCESS",
        "from": from_account,
        "to": to_account,
        "amount": amount,
        "new_source_balance": new_src_bal,
        "message": "Virement effectué avec succès."
    }


    
    return {
        "status": "SUCCESS",
        "from": from_account,
        "to": to_account,
        "amount": amount,
        "new_source_balance": new_src_bal,
        "message": "Virement effectué avec succès."
    }


def generate_statement_pdf(account_identifier: str) -> Dict[str, Any]:
    """Génère un PDF d'extrait de compte SIMPLIFIÉ (Noir et Blanc, Standard)."""
    account_number = _resolve_account_number(account_identifier)
    if not account_number:
        return {"status": "ERROR", "error": f"Compte ou client '{account_identifier}' introuvable."}
        
    try:
        from fpdf import FPDF
    except ImportError:
        from fpdf2 import FPDF
    import os
    import time
    
    # 1. Données
    stmt = generate_statement(account_number)
    acc = _accounts.find_one({"account_number": account_number})
    if not acc:
        return {"status": "ERROR", "error": "Compte non trouvé (après résolution)."}
    
    # Résolution client
    from bson import ObjectId
    cust_id_obj = ObjectId(acc["customer_id"]) if isinstance(acc["customer_id"], str) else acc["customer_id"]
    cust = _customers.find_one({"_id": cust_id_obj})
    if not cust:
        return {"status": "ERROR", "error": "Client introuvable."}

    cust_name = f"{cust['personal_info'].get('prenom', '').capitalize()} {cust['personal_info'].get('nom', '').upper()}"
    
    # 2. PDF Ultra Simple (Arial, No Color)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 20, "BH BANK - EXTRAIT DE COMPTE", border=0, ln=1, align="L")
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Client : {cust_name}", ln=1)
    pdf.cell(0, 10, f"Compte : {account_number}", ln=1)
    pdf.cell(0, 10, f"Solde : {acc.get('balance', 0.0)} DT", ln=1)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 10, "Date", border=1)
    pdf.cell(100, 10, "Libelle", border=1)
    pdf.cell(30, 10, "Montant", border=1, ln=1)
    
    pdf.set_font("Arial", "", 10)
    for line in stmt.get("statement_lines", []):
        date = str(line.get("date", ""))[:10]
        label = str(line.get("label", ""))[:50]
        amt = f"{line.get('amount', 0.0):.2f}"
        
        pdf.cell(30, 8, date, border=1)
        pdf.cell(100, 8, label, border=1)
        pdf.cell(30, 8, amt, border=1, ln=1)

    if not stmt.get("statement_lines"):
        pdf.cell(160, 10, "Aucune transaction.", border=1, ln=1, align="C")

    # 3. Save
    folder = "web_rag_test/temp_statements"
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    
    filename = f"extrait_{int(time.time())}.pdf"
    filepath = os.path.join(folder, filename)
    pdf.output(filepath)
    
    return {
        "status": "SUCCESS",
        "pdf_url": f"/temp_statements/{filename}",
        "filename": filename
    }


def block_card(customer_id: Optional[str], card_id: str, reason: str = "SECURITY") -> Dict[str, Any]:
    """Action spécifique demandée par l'agent."""
    return manage_card(card_id, "BLOCK", reason)


def unblock_card(customer_id: Optional[str], card_id: str) -> Dict[str, Any]:
    """Action spécifique demandée par l'agent."""
    return manage_card(card_id, "UNBLOCK")


def manage_card(card_number: str, action: str = "BLOCK", reason: str = "SECURITY") -> Dict[str, Any]:
    """
    Blocks or unblocks a card.
    """
    status = "BLOCKED" if action.upper() == "BLOCK" else "ACTIVE"
    
    # Tentative d'update
    result = _cards.update_one(
        {"card_number": card_number},
        {"$set": {"status": status, "last_updated": _dt.datetime.now()}, 
         "$push": {"history": {"action": action, "reason": reason, "date": _dt.datetime.now()}}}
    )

    if result.matched_count == 0:
        # If card doesn't exist, we "create" it to simulate the state (simplified for demo)
        _cards.insert_one({
            "card_number": card_number,
            "status": status,
            "history": [{"action": action, "reason": reason, "date": _dt.datetime.now()}]
        })

    return {
        "card_number": card_number,
        "action": action,
        "new_status": status,
        "status": "SUCCESS"
    }


def fx_rate(pair: str) -> Dict[str, Any]:
    if not pair:
        pair = "EUR/USD"
    pair = pair.upper().replace(" ", "")

    # Tentative de récupération depuis la base
    params = _params.find_one({"param_type": "fx_rates"}) or {}
    rate = params.get(pair)
    
    if rate is None:
        # Fallback Mock enrichi
        mock_rates = {"EUR/USD": 1.08, "USD/EUR": 0.93, "EUR/TND": 3.40, "USD/TND": 3.12}
        rate = mock_rates.get(pair)

    if rate is None:
        return {"pair": pair, "status": "NOT_FOUND", "rate": None}

    return {"pair": pair, "rate": rate, "status": "OK", "source": "BH Bank FX Service"}


def product_info(product_type: str) -> Dict[str, Any]:
    key = (product_type or "credit").strip().lower()
    
    # Try to find rates in bank_params
    params = _params.find_one({"param_type": "global_rates"}) or {}
    tmm = params.get("tmm", 0.08) # BH TMM est proche de 8%
    
    catalog = {
        "credit": f"Nos crédits sont basés sur le TMM actuel ({tmm*100:.2f}%). Nous offrons des crédits consommation, voiture et aménagement.",
        "epargne": "Nos comptes épargne offrent un taux de rémunération avantageux calculé selon votre solde moyen.",
        "carte": "Nous disposons d'une large gamme de cartes: Visa, Mastercard, et cartes locales.",
    }
    
    # Simple mapping
    if "conso" in key or "consommation" in key:
        marge = params.get("marge_additionnelle_consommation", 0.05)
        desc = f"Crédit Consommation: Taux = TMM + {marge*100:.2f}% (Total env. {(tmm+marge)*100:.2f}%)"
    elif "voiture" in key or "auto" in key:
        marge = params.get("marge_additionnelle_voiture", 0.035)
        desc = f"Crédit Voiture: Taux = TMM + {marge*100:.2f}% (Total env. {(tmm+marge)*100:.2f}%)"
    else:
        desc = catalog.get(key, "Veuillez préciser le type de produit (Crédit, Épargne, Carte).")

    return {"product_type": key, "description": desc, "status": "OK"}


def create_customer(nom: str, prenom: str = "", cin: str = "") -> Dict[str, Any]:
    """Cree un nouveau client dans la base, ou retourne l'existant."""
    print(f"[DB] create_customer call: nom={nom}, prenom={prenom}, cin={cin}")
    # Check if exists by name + cin
    query = {"personal_info.nom": {"$regex": f"^{nom}$", "$options": "i"}}
    if prenom:
        query["personal_info.prenom"] = {"$regex": f"^{prenom}$", "$options": "i"}
    # Check if CIN exists
    if cin:
        existing_cin = _customers.find_one({"personal_info.cin": str(cin)})
        if existing_cin:
            return {
                "status": "EXISTS",
                "message": f"Un client avec le CIN {cin} existe déjà.",
                "customer_id": str(existing_cin["_id"])
            }

    # Check if Name/Prenom exists
    existing = _customers.find_one(query)
    if existing:
        return {
            "status": "EXISTS",
            "customer_id": str(existing["_id"]),
            "name": f"{existing['personal_info'].get('prenom', '')} {existing['personal_info'].get('nom', '')}".strip(),
            "message": "Client déjà existant dans la base."
        }

    new_doc = {
        "personal_info": {
            "nom": nom,
            "prenom": prenom,
            "cin": cin
        },
        "created_at": _now_iso(),
        "transactions": []
    }
    res = _customers.insert_one(new_doc)
    return {
        "status": "SUCCESS",
        "customer_id": str(res.inserted_id),
        "name": f"{prenom} {nom}".strip()
    }

