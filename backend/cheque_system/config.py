import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
RESULT_DIR = os.path.join(BASE_DIR, "static", "results")
CROP_DIR = os.path.join(BASE_DIR, "static", "crops")

DATA_DIR = os.path.join(BASE_DIR, "data")
SIGNATURE_DIR = os.path.join(DATA_DIR, "signatures")
CHEQUE_DATA_DIR = os.path.join(DATA_DIR, "cheque_tunisie")
FACTURE_DATA_DIR = os.path.join(DATA_DIR, "facture")

VECTOR_INDEX_PATH = os.path.join(BASE_DIR, "chatbot_vector_index")

DB_PATH = os.path.join(BASE_DIR, "database.db")
MODEL_PATH = os.path.join(BASE_DIR, "model_final.pth")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL", "llama3.2")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision")

CLASS_NAMES = [
    "signature",
    "amount",
    "amount_words",
    "date",
    "payee",
    "signature_f",
    "signature_g"
]

for folder in [
    UPLOAD_DIR,
    RESULT_DIR,
    CROP_DIR,
    DATA_DIR,
    SIGNATURE_DIR,
    CHEQUE_DATA_DIR,
    FACTURE_DATA_DIR,
    VECTOR_INDEX_PATH
]:
    os.makedirs(folder, exist_ok=True)