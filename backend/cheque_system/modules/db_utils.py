import sqlite3
import re
from config import DB_PATH


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount TEXT NOT NULL,
            signature_path TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def normalize_text(text):
    if text is None:
        return ""

    text = str(text).lower().strip()
    text = text.replace(" ", "")
    text = text.replace(".", "")
    text = text.replace(",", "")
    text = re.sub(r"[^a-zA-Z0-9\u0600-\u06FF]", "", text)

    return text


def normalize_amount(amount):
    if amount is None:
        return None

    amount = str(amount).strip()
    amount = amount.replace(" ", "")
    amount = amount.replace(",", ".")
    amount = re.sub(r"[^0-9.]", "", amount)

    if amount == "":
        return None

    try:
        return round(float(amount), 2)
    except Exception:
        return None


def find_client_in_db(client_text):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients")
    clients = cursor.fetchall()
    conn.close()

    normalized_input = normalize_text(client_text)

    if not normalized_input:
        return None

    best_client = None

    for client in clients:
        normalized_name = normalize_text(client["name"])

        if normalized_input == normalized_name:
            return dict(client)

        if normalized_input in normalized_name or normalized_name in normalized_input:
            best_client = dict(client)

    return best_client


def verify_amount_in_db(amount_text, client):
    if not client:
        return False

    detected_amount = normalize_amount(amount_text)
    db_amount = normalize_amount(client["amount"])

    if detected_amount is None or db_amount is None:
        return False

    return detected_amount == db_amount