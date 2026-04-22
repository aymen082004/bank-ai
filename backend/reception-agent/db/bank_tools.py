from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add the current directory to sys.path to allow imports from db
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from langchain_core.tools import tool
import bank_actions_db

@tool
def search_bank_docs(query: str) -> str:
    """Recherche dans la documentation interne et sur le Web pour des questions générales, news ou infos d'actualité sur la BH Bank."""
    return bank_actions_db.search_faiss(query)


@tool
def get_customer_balance(customer_id: str, account_id: Optional[str] = None) -> str:
    """Récupère le solde et l'état des comptes d'un client. 
    L'identifiant peut être un nom, un CIN ou un numéro de compte."""
    result = bank_actions_db.get_balance(customer_id, account_id)
    return str(result)

@tool
def open_new_account(customer_id: str, account_type: str = "courant", initial_deposit: float = 0.0) -> str:
    """Ouvre un nouveau compte pour un client existant. 
    Types possibles: courant, epargne, devises."""
    result = bank_actions_db.open_account(customer_id, account_type, initial_deposit)
    return str(result)

@tool
def bank_transfer(from_account: str, to_account: str, amount: float, description: str = "Virement") -> str:
    """Effectue un virement entre deux comptes. 
    Les identifiants peuvent être des numéros de compte, des noms ou des CIN."""
    result = bank_actions_db.perform_transfer(from_account, to_account, amount, description)
    return str(result)

@tool
def generate_account_statement(account_identifier: str) -> str:
    """Génère un extrait de compte au format PDF et retourne le lien de téléchargement. 
    L'identifiant peut être un numéro de compte, un CIN ou un nom."""
    result = bank_actions_db.generate_statement_pdf(account_identifier)
    return str(result)

@tool
def manage_bank_card(card_id: str, action: str = "BLOCK", reason: str = "SECURITY") -> str:
    """Bloque (BLOCK) ou débloque (UNBLOCK) une carte bancaire."""
    result = bank_actions_db.manage_card(card_id, action, reason)
    return str(result)

@tool
def get_exchange_rate(pair: str = "EUR/TND") -> str:
    """Récupère le cours de change pour une paire de devises donnée (ex: EUR/TND, USD/TND)."""
    result = bank_actions_db.fx_rate(pair)
    return str(result)

@tool
def get_product_details(product_type: str) -> str:
    """Obtient des informations détaillées sur un produit spécifique (credit, epargne, carte)."""
    result = bank_actions_db.product_info(product_type)
    return str(result)

@tool
def register_new_customer(nom: str, prenom: str = "", cin: str = "") -> str:
    """Enregistre un nouveau client dans la base de données de la banque."""
    result = bank_actions_db.create_customer(nom, prenom, cin)
    return str(result)

AVAILABLE_BANK_TOOLS = [
    search_bank_docs,
    get_customer_balance,
    open_new_account,
    bank_transfer,
    generate_account_statement,
    manage_bank_card,
    get_exchange_rate,
    get_product_details,
    register_new_customer
]
