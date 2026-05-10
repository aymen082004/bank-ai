import json
import re
import requests
from config import OLLAMA_URL, OLLAMA_VISION_MODEL
from modules.image_utils import image_to_base64


def clean_json_response(text):
    if not text:
        return {}

    text = text.strip()
    text = text.replace("```json", "")
    text = text.replace("```", "")
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return {}

    return {}


def extract_with_ollama(image_path, field_name):
    image_b64 = image_to_base64(image_path)

    if field_name == "client":
        prompt = """
Tu es un système d'extraction depuis un chèque bancaire.
Extrais uniquement le nom du client ou bénéficiaire.
Réponds uniquement en JSON valide.

Format:
{
  "field": "client",
  "value": "",
  "confidence": 0.0
}
"""
    elif field_name == "amount":
        prompt = """
Tu es un système d'extraction depuis un chèque bancaire.
Extrais uniquement le montant numérique.
Réponds uniquement en JSON valide.

Format:
{
  "field": "amount",
  "value": "",
  "confidence": 0.0
}
"""
    else:
        prompt = f"""
Extrais le champ {field_name} depuis cette image.
Réponds uniquement en JSON:
{{
  "field": "{field_name}",
  "value": "",
  "confidence": 0.0
}}
"""

    payload = {
        "model": OLLAMA_VISION_MODEL,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()

        data = response.json()
        raw_response = data.get("response", "")
        parsed = clean_json_response(raw_response)

        return {
            "field": parsed.get("field", field_name),
            "value": str(parsed.get("value", "")).strip(),
            "confidence": float(parsed.get("confidence", 0.0) or 0.0),
            "raw": raw_response
        }

    except requests.exceptions.ConnectionError:
        return {
            "field": field_name,
            "value": "",
            "confidence": 0.0,
            "error": "Ollama n'est pas lancé. Lance: ollama serve"
        }

    except Exception as e:
        return {
            "field": field_name,
            "value": "",
            "confidence": 0.0,
            "error": str(e)
        }


def extract_multimodal_with_ollama(image_path, document_type):
    image_b64 = image_to_base64(image_path)

    if document_type == "cheque_tunisie":
        schema = """
{
  "document_type": "cheque_tunisie",
  "payee": "",
  "drawer": "",
  "bank_name": "",
  "cheque_number": "",
  "account_number": "",
  "amount_numeric": "",
  "amount_words": "",
  "currency": "",
  "date": "",
  "signature_present": false,
  "rib_or_iban": "",
  "visible_issues": [],
  "confidence": 0.0
}
"""
    elif document_type == "facture":
        schema = """
{
  "document_type": "facture",
  "supplier_name": "",
  "client_name": "",
  "invoice_number": "",
  "date": "",
  "tax_id": "",
  "total_ht": "",
  "tva": "",
  "total_ttc": "",
  "currency": "",
  "line_items": [],
  "visible_issues": [],
  "confidence": 0.0
}
"""
    else:
        schema = """
{
  "document_type": "unknown",
  "detected_type": "",
  "fields": {},
  "visible_issues": [],
  "confidence": 0.0
}
"""

    prompt = f"""
Vous êtes un extracteur multimodal spécialisé en documents financiers.
Type de document attendu: {document_type}

Retournez uniquement un JSON valide.
Ne donnez aucune explication.
Ne devinez pas.

Schéma:
{schema}
"""

    payload = {
        "model": OLLAMA_VISION_MODEL,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=240)
        response.raise_for_status()

        raw = response.json().get("response", "")
        parsed = clean_json_response(raw)

        return {
            "raw": raw,
            "data": parsed
        }

    except requests.exceptions.ConnectionError:
        return {
            "raw": "",
            "data": {},
            "error": "Ollama n'est pas lancé. Lancez: ollama serve"
        }

    except Exception as e:
        return {
            "raw": "",
            "data": {},
            "error": str(e)
        }