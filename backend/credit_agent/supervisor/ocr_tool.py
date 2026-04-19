from pdf2image import convert_from_path
import pytesseract
import re
import json


def clean_amount(x):
    """Convert French-formatted number to float"""
    if not x:
        return None
    x = x.replace(" ", "").replace(",", ".")
    try:
        return float(x)
    except:
        return None


def extract_payslip_data(pdf_path):
    """
    Extract payslip data from PDF using OCR
    Returns structured JSON with unified credit_entreprise field
    """

    # 1️⃣ OCR PDF
    pages = convert_from_path(pdf_path, dpi=300)
    full_text = ""

    for page in pages:
        text = pytesseract.image_to_string(page, config="--psm 6")
        full_text += text + "\n"

    data = {}

    # 2️⃣ Amount extraction
    amount_patterns = {
        "salary_net": r"Salaire\s*net\s*[:=]?\s*([\d\s.,]+)",
        "avance": r"Avance\s*[:=]?\s*([\d\s.,]+)",
        "credit_entreprise_raw": r"Cr[eé]dit\s*entreprise\s*[:=]?\s*([\d\s.,]+)",
        "cin": r"C[I1l]N\s*[:=]?\s*([0-9]{6,10})"
    }

    for key, pattern in amount_patterns.items():
        match = re.search(pattern, full_text, re.IGNORECASE)
        data[key] = match.group(1).strip() if match else None

    # 3️⃣ Combine Avance + Crédit entreprise → ONE FIELD
    avance_val = clean_amount(data.get("avance"))
    credit_val = clean_amount(data.get("credit_entreprise_raw"))
    # print("Values of cin: ", data.get("cin"))
    # print(avance_val, credit_val)

    final_value = None

    if avance_val and credit_val:
        final_value = avance_val + credit_val
    elif avance_val:
        final_value = avance_val
    elif credit_val:
        final_value = credit_val

    # Store always as credit_entreprise (French format optional)
    if final_value is not None:
        data["credit_entreprise"] = str(final_value).replace(".", ",")
    else:
        data["credit_entreprise"] = None

    # Remove intermediate fields
    data.pop("avance", None)
    data.pop("credit_entreprise_raw", None)

    # 4️⃣ Nom & Prénom
    match_nom = re.search(r"Nom\s*&?\s*Prénom\s*[:=]?\s*([A-Za-z\s]+)", full_text, re.IGNORECASE)
    if match_nom:
        nom = match_nom.group(1).strip()
        nom = re.split(r'\n|CIN', nom)[0].strip()
        data["nom_prenom"] = nom
    else:
        data["nom_prenom"] = None

    # 5️⃣ Numéro de compte
    compte_match = re.search(r"Virement.*?(\b[\dA-Z]{10,}\b)", full_text, re.IGNORECASE)
    data["numero_compte"] = compte_match.group(1).strip() if compte_match else None

    # 6️⃣ Date de paiement
    date_match = re.search(r"Date\s*de\s*paiement\s*[:=]?\s*([\d/.\-]+)", full_text, re.IGNORECASE)
    data["date_paiement"] = date_match.group(1).strip() if date_match else None

    # 7️⃣ Clean salary_net format (optional)
    if data.get("salary_net"):
        val = clean_amount(data["salary_net"])
        data["salary_net"] = str(val).replace(".", ",") if val else None

    data["cin"] = data.get("cin")

    return data


# ------------------------------
# Example usage
# ------------------------------
if __name__ == "__main__":
    # pdf_file = r"F:\Projects\FastFin_Agent\Res\fiche-de-Paie-Excel-Tunisie-CE.pdf"
    pdf_file = r"F:\Projects\FastFin_Agent\Res\fiche-de-Paie-Excel-Tunisie-CorrMiss.pdf"

    result = extract_payslip_data(pdf_file)

    print(json.dumps(result, indent=2, ensure_ascii=False))