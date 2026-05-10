import os
import cv2
import uuid
import sqlite3
import re
import json
import base64
import requests
from typing import Any, Dict, List

from flask import Flask, render_template, request, jsonify

from detectron2.config import get_cfg
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.language_models.llms import LLM
from langchain_core.documents import Document


# ==========================================================
# FLASK CONFIG
# ==========================================================

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
RESULT_FOLDER = os.path.join(BASE_DIR, "static", "results")
CROP_FOLDER = os.path.join(BASE_DIR, "static", "crops")

DATA_DIR = os.path.join(BASE_DIR, "data")
SIGNATURE_FOLDER = os.path.join(DATA_DIR, "signatures")
CHEQUE_DATA_DIR = os.path.join(DATA_DIR, "cheque_tunisie")
FACTURE_DATA_DIR = os.path.join(DATA_DIR, "facture")
VECTOR_INDEX_PATH = os.path.join(BASE_DIR, "chatbot_vector_index")

DB_PATH = os.path.join(BASE_DIR, "database.db")
MODEL_PATH = os.path.join(BASE_DIR, "model_final.pth")

for folder in [
    UPLOAD_FOLDER,
    RESULT_FOLDER,
    CROP_FOLDER,
    DATA_DIR,
    SIGNATURE_FOLDER,
    CHEQUE_DATA_DIR,
    FACTURE_DATA_DIR,
    VECTOR_INDEX_PATH
]:
    os.makedirs(folder, exist_ok=True)


# ==========================================================
# OLLAMA CONFIG
# ==========================================================

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL", "llama3.2")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision")


# ==========================================================
# DETECTRON2 CONFIG
# ==========================================================

CLASS_NAMES = [
    "signature",
    "amount",
    "amount_words",
    "date",
    "payee",
    "signature_f",
    "signature_g"
]

cfg = get_cfg()
cfg.merge_from_file(
    model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml")
)

cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(CLASS_NAMES)
cfg.MODEL.WEIGHTS = MODEL_PATH
cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
cfg.MODEL.DEVICE = "cpu"

predictor = DefaultPredictor(cfg)

metadata = MetadataCatalog.get("bankia_dataset")
metadata.thing_classes = CLASS_NAMES


# ==========================================================
# SQLITE
# ==========================================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
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


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


init_db()


# ==========================================================
# HELPERS
# ==========================================================

def web_path(path):
    if path is None:
        return None

    rel = os.path.relpath(path, BASE_DIR)
    return "/" + rel.replace("\\", "/")


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


def image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


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


def crop_bbox(image, bbox, padding=15):
    x1, y1, x2, y2 = [int(v) for v in bbox]

    h, w = image.shape[:2]

    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w, x2 + padding)
    y2 = min(h, y2 + padding)

    return image[y1:y2, x1:x2]


def save_crop(crop, prefix, filename):
    crop_filename = f"{prefix}_{filename}"
    crop_path = os.path.join(CROP_FOLDER, crop_filename)
    cv2.imwrite(crop_path, crop)
    return crop_path


# ==========================================================
# CLIENT DATABASE
# ==========================================================

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


# ==========================================================
# OLLAMA VISION
# ==========================================================

def extract_with_ollama(image_path, field_name):
    image_b64 = image_to_base64(image_path)

    if field_name == "client":
        prompt = """
Tu es un système d'extraction depuis un chèque bancaire.

L'image contient le nom du client ou bénéficiaire.

Ta tâche:
Extraire uniquement le nom visible.

Règles:
- Réponds uniquement en JSON valide.
- Ne donne aucune explication.
- Ne devine pas.
- Si c'est illisible, mets value à "".

Format exact:
{
  "field": "client",
  "value": "",
  "confidence": 0.0
}
"""
    elif field_name == "amount":
        prompt = """
Tu es un système d'extraction depuis un chèque bancaire.

L'image contient un montant numérique.

Ta tâche:
Extraire uniquement le montant.

Règles:
- Réponds uniquement en JSON valide.
- Ne donne aucune explication.
- Ne devine pas.
- Si c'est illisible, mets value à "".
- Utilise un point comme séparateur décimal si nécessaire.

Format exact:
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
  "qr_code_present": false,
  "ceiling_present": false,
  "validity_period_present": false,
  "bank_identifier_present": false,
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

Type de document attendu:
{document_type}

Analysez l'image fournie.

Retournez uniquement un JSON valide.
Ne donnez aucune explication.
Ne devinez pas.
Si une valeur est absente ou illisible, mettez "" ou false.

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


# ==========================================================
# SIGNATURE VERIFICATION
# ==========================================================

def remove_empty_borders(binary_img):
    coords = cv2.findNonZero(binary_img)

    if coords is None:
        return binary_img

    x, y, w, h = cv2.boundingRect(coords)
    return binary_img[y:y + h, x:x + w]


def preprocess_signature(signature_img):
    gray = cv2.cvtColor(signature_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    _, binary = cv2.threshold(
        gray,
        180,
        255,
        cv2.THRESH_BINARY_INV
    )

    binary = remove_empty_borders(binary)
    binary = cv2.resize(binary, (400, 160), interpolation=cv2.INTER_AREA)

    return binary


def signature_template_score(signature_crop, reference_signature):
    sig1 = preprocess_signature(signature_crop)
    sig2 = preprocess_signature(reference_signature)

    result = cv2.matchTemplate(sig1, sig2, cv2.TM_CCOEFF_NORMED)
    score = float(result.max())

    if score < 0:
        score = 0.0

    return round(score, 3)


def signature_orb_score(signature_crop, reference_signature):
    sig1 = preprocess_signature(signature_crop)
    sig2 = preprocess_signature(reference_signature)

    orb = cv2.ORB_create(nfeatures=1500)

    kp1, des1 = orb.detectAndCompute(sig1, None)
    kp2, des2 = orb.detectAndCompute(sig2, None)

    if des1 is None or des2 is None:
        return 0.0

    if len(kp1) == 0 or len(kp2) == 0:
        return 0.0

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(des1, des2)

    if not matches:
        return 0.0

    good_matches = [m for m in matches if m.distance < 65]
    score = len(good_matches) / max(len(kp1), len(kp2), 1)

    return round(float(score), 3)


def signature_similarity(signature_crop, reference_signature):
    template_score = signature_template_score(signature_crop, reference_signature)
    orb_score = signature_orb_score(signature_crop, reference_signature)

    final_score = (template_score * 0.75) + (orb_score * 0.25)

    return {
        "template_score": template_score,
        "orb_score": orb_score,
        "final_score": round(final_score, 3)
    }


def verify_signature(signature_crop, client):
    if not client:
        return {
            "is_correct": False,
            "status": "client_introuvable",
            "score": 0,
            "template_score": 0,
            "orb_score": 0,
            "message": "Client introuvable, impossible de vérifier la signature."
        }

    signature_path = client["signature_path"]

    if not os.path.exists(signature_path):
        return {
            "is_correct": False,
            "status": "signature_reference_absente",
            "score": 0,
            "template_score": 0,
            "orb_score": 0,
            "message": "Signature de référence introuvable."
        }

    reference_signature = cv2.imread(signature_path)

    if reference_signature is None:
        return {
            "is_correct": False,
            "status": "signature_reference_invalide",
            "score": 0,
            "template_score": 0,
            "orb_score": 0,
            "message": "Impossible de lire la signature de référence."
        }

    scores = signature_similarity(signature_crop, reference_signature)
    final_score = scores["final_score"]

    if final_score >= 0.45:
        status = "probablement_correcte"
        message = "Signature probablement correcte."
        is_correct = True
    elif final_score >= 0.25:
        status = "a_verifier"
        message = "Signature incertaine, vérification manuelle recommandée."
        is_correct = False
    else:
        status = "differente"
        message = "Signature probablement différente."
        is_correct = False

    return {
        "is_correct": is_correct,
        "status": status,
        "score": final_score,
        "template_score": scores["template_score"],
        "orb_score": scores["orb_score"],
        "message": message
    }


# ==========================================================
# DETECTION
# ==========================================================

def get_best_detection(detections, class_name):
    filtered = [d for d in detections if d["class"] == class_name]

    if not filtered:
        return None

    return max(filtered, key=lambda x: x["score"])


def get_best_detection_multi(detections, class_names):
    filtered = [d for d in detections if d["class"] in class_names]

    if not filtered:
        return None

    return max(filtered, key=lambda x: x["score"])


def detect_fields(image):
    outputs = predictor(image)
    instances = outputs["instances"].to("cpu")

    boxes = instances.pred_boxes.tensor.numpy()
    classes = instances.pred_classes.numpy()
    scores = instances.scores.numpy()

    detections = []

    for box, cls, score in zip(boxes, classes, scores):
        detections.append({
            "class": CLASS_NAMES[int(cls)],
            "score": round(float(score), 3),
            "bbox": [round(float(x), 2) for x in box]
        })

    return detections, instances


def draw_result_image(image, instances):
    visualizer = Visualizer(
        image[:, :, ::-1],
        metadata=metadata,
        scale=0.8
    )

    result = visualizer.draw_instance_predictions(instances)
    return result.get_image()[:, :, ::-1]


# ==========================================================
# RAG SYSTEM
# ==========================================================

class OllamaLLM(LLM):
    model: str = OLLAMA_TEXT_MODEL
    ollama_url: str = OLLAMA_URL

    def _call(self, prompt: str, stop=None, run_manager=None, **kwargs) -> str:
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0}
            }

            response = requests.post(self.ollama_url, json=payload, timeout=240)
            response.raise_for_status()

            data = response.json()
            return data.get("response", "").strip()

        except requests.exceptions.ConnectionError:
            return "Erreur: Ollama n'est pas lancé. Lancez la commande: ollama serve"

        except Exception as e:
            return f"Erreur Ollama: {str(e)}"

    @property
    def _llm_type(self):
        return "ollama"

    @property
    def _identifying_params(self):
        return {
            "model": self.model,
            "ollama_url": self.ollama_url
        }


def safe_json_load(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def flatten_json_to_text(obj: Any, prefix: str = "") -> str:
    if isinstance(obj, dict):
        parts = []

        for key, value in obj.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            parts.append(flatten_json_to_text(value, new_prefix))

        return "\n".join(parts)

    if isinstance(obj, list):
        return "\n".join(flatten_json_to_text(item, prefix) for item in obj)

    return f"{prefix}: {obj}"


def load_json_documents_from_folder(folder: str, domain: str) -> List[Document]:
    documents = []

    if not os.path.exists(folder):
        return documents

    for filename in os.listdir(folder):
        if not filename.lower().endswith(".json"):
            continue

        path = os.path.join(folder, filename)

        try:
            data = safe_json_load(path)
            items = data if isinstance(data, list) else [data]

            for item in items:
                if isinstance(item, dict):
                    title = item.get("titre", item.get("title", filename))
                    doc_type = item.get("type", domain)
                    source = item.get("source", filename)
                    description = item.get("description", "")
                    content = item.get("contenu", item.get("content", ""))

                    if not content:
                        content = flatten_json_to_text(item)

                    text = f"""
Domaine: {domain}
Titre: {title}
Type: {doc_type}
Source: {source}
Description: {description}
Contenu:
{content}
"""

                    documents.append(
                        Document(
                            page_content=text,
                            metadata={
                                "domain": domain,
                                "title": title,
                                "type": doc_type,
                                "source": source,
                                "file": filename
                            }
                        )
                    )

        except Exception as e:
            print(f"Erreur lecture JSON {path}: {e}")

    return documents


def load_all_documents() -> List[Document]:
    documents = []

    documents.extend(load_json_documents_from_folder(CHEQUE_DATA_DIR, "cheque_tunisie"))
    documents.extend(load_json_documents_from_folder(FACTURE_DATA_DIR, "facture"))

    if not documents:
        documents.append(
            Document(
                page_content="Base documentaire vide.",
                metadata={"domain": "default", "source": "default"}
            )
        )

    return documents


def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name="distiluse-base-multilingual-cased-v1",
        model_kwargs={"device": "cpu"}
    )


def is_valid_faiss_index(index_path: str) -> bool:
    faiss_file = os.path.join(index_path, "index.faiss")
    pkl_file = os.path.join(index_path, "index.pkl")

    return (
        os.path.exists(faiss_file)
        and os.path.exists(pkl_file)
        and os.path.getsize(faiss_file) > 100
        and os.path.getsize(pkl_file) > 100
    )


def build_vector_index():
    print("Construction du nouvel index FAISS...")

    embedding = get_embedding_model()
    raw_docs = load_all_documents()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=180,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    split_docs = splitter.split_documents(raw_docs)
    vectorstore = FAISS.from_documents(split_docs, embedding)
    vectorstore.save_local(VECTOR_INDEX_PATH)

    print(f"Index FAISS construit avec {len(split_docs)} chunks.")
    return vectorstore


def load_or_create_vector_index(force_rebuild: bool = False):
    embedding = get_embedding_model()

    if not force_rebuild and is_valid_faiss_index(VECTOR_INDEX_PATH):
        print("Chargement de l'index FAISS existant...")

        return FAISS.load_local(
            VECTOR_INDEX_PATH,
            embedding,
            allow_dangerous_deserialization=True
        )

    return build_vector_index()


vectorstore = None
retriever = None
llm = None
rag_ready = False


def initialize_rag(force_rebuild: bool = False):
    global vectorstore, retriever, llm, rag_ready

    vectorstore = load_or_create_vector_index(force_rebuild=force_rebuild)

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 10}
    )

    llm = OllamaLLM()
    rag_ready = True

    print("RAG initialisé avec succès.")


def format_docs(docs):
    parts = []

    for i, doc in enumerate(docs, start=1):
        metadata = doc.metadata or {}

        source = metadata.get("source", "unknown")
        domain = metadata.get("domain", "unknown")
        title = metadata.get("title", "")
        file = metadata.get("file", "")

        parts.append(
            f"""
[Document {i}]
Domaine: {domain}
Titre: {title}
Source: {source}
Fichier: {file}

{doc.page_content}
"""
        )

    return "\n\n---\n\n".join(parts)


def get_retrieved_docs(question: str, k: int = 6):
    if not retriever:
        return []

    docs = retriever.invoke(question)
    return docs[:k]


def format_retrieved_sources_for_api(retrieved_docs):
    sources = []

    for rank, doc in enumerate(retrieved_docs, start=1):
        metadata = doc.metadata or {}

        sources.append({
            "rank": rank,
            "domain": metadata.get("domain", ""),
            "title": metadata.get("title", ""),
            "source": metadata.get("source", ""),
            "file": metadata.get("file", ""),
            "preview": doc.page_content[:500]
        })

    return sources


def ask_rag_with_docs(question: str, k: int = 6):
    if not llm or not retriever:
        return {
            "answer": "RAG non disponible.",
            "docs": []
        }

    docs = get_retrieved_docs(question, k=k)
    context = format_docs(docs)

    prompt = f"""
Vous êtes un assistant RAG spécialisé dans:
1. Les chèques bancaires en Tunisie.
2. Les normes et contrôles des chèques dans le monde.
3. Les factures et documents financiers.

Vous devez répondre uniquement avec le contexte fourni.
Si le contexte ne suffit pas, dites:
"Je ne trouve pas cette information dans la base documentaire."

Contexte:
{context}

Question:
{question}

Instructions:
- Répondez en français.
- Soyez clair et structuré.
- Distinguez les règles tunisiennes et les règles générales internationales.
- Mentionnez les sources présentes dans le contexte quand elles existent.
- Ne donnez pas de décision juridique définitive.
- Donnez une analyse documentaire, technique et réglementaire.

Réponse:
"""

    answer = llm.invoke(prompt)

    return {
        "answer": answer,
        "docs": docs
    }


def ask_rag(question: str) -> str:
    result = ask_rag_with_docs(question, k=6)
    return result["answer"]


def automatic_rag_evaluation(question: str, answer: str, retrieved_docs) -> Dict[str, Any]:
    if not llm:
        return {"error": "LLM non disponible pour l'évaluation."}

    if not retrieved_docs:
        return {
            "context_relevance_score": 0.0,
            "answer_groundedness_score": 0.0,
            "answer_completeness_score": 0.0,
            "source_coverage_score": 0.0,
            "hallucination_risk_score": 1.0,
            "final_quality_score": 0.0,
            "decision": "faible",
            "explanation": "Aucun contexte récupéré.",
            "recommendations": [
                "Ajouter plus de documents dans la base RAG.",
                "Reconstruire l'index FAISS."
            ]
        }

    context = format_docs(retrieved_docs)

    eval_prompt = f"""
Tu es un évaluateur RAG.

QUESTION:
{question}

CONTEXTE:
{context}

RÉPONSE:
{answer}

Retourne uniquement un JSON valide.

Format exact:
{{
  "context_relevance_score": 0.0,
  "answer_groundedness_score": 0.0,
  "answer_completeness_score": 0.0,
  "source_coverage_score": 0.0,
  "hallucination_risk_score": 0.0,
  "final_quality_score": 0.0,
  "decision": "bonne | moyenne | faible",
  "explanation": "",
  "recommendations": []
}}
"""

    raw_eval = llm.invoke(eval_prompt)
    parsed_eval = clean_json_response(raw_eval)

    if not parsed_eval:
        return {
            "raw_evaluation": raw_eval,
            "error": "Impossible de parser l'évaluation JSON."
        }

    return parsed_eval


try:
    initialize_rag(force_rebuild=False)
except Exception as e:
    rag_ready = False
    print(f"Erreur initialisation RAG: {e}")


# ==========================================================
# ROUTES
# ==========================================================

@app.route("/")
def home():
    return render_template("cheque.html")


@app.route("/cheque")
def cheque_page():
    return render_template("cheque.html")


@app.route("/rag")
def rag_page():
    return render_template("rag.html")


@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    safe_name = file.filename.replace("\\", "_").replace("/", "_")
    filename = str(uuid.uuid4()) + "_" + safe_name
    image_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(image_path)

    image = cv2.imread(image_path)

    if image is None:
        return jsonify({"error": "Invalid image"}), 400

    detections, instances = detect_fields(image)

    client_detection = get_best_detection(detections, "payee")
    amount_detection = get_best_detection(detections, "amount")

    signature_detection = get_best_detection_multi(
        detections,
        ["signature", "signature_f", "signature_g"]
    )

    client_text = ""
    amount_text = ""

    client_crop_path = None
    amount_crop_path = None
    signature_crop_path = None

    client_ollama_result = None
    amount_ollama_result = None

    if client_detection:
        client_crop = crop_bbox(image, client_detection["bbox"], padding=20)
        client_crop_path = save_crop(client_crop, "client", filename)

        client_ollama_result = extract_with_ollama(
            client_crop_path,
            "client"
        )

        client_text = client_ollama_result.get("value", "")

    if amount_detection:
        amount_crop = crop_bbox(image, amount_detection["bbox"], padding=20)
        amount_crop_path = save_crop(amount_crop, "amount", filename)

        amount_ollama_result = extract_with_ollama(
            amount_crop_path,
            "amount"
        )

        amount_text = amount_ollama_result.get("value", "")

    signature_crop = None

    if signature_detection:
        signature_crop = crop_bbox(image, signature_detection["bbox"], padding=30)
        signature_crop_path = save_crop(signature_crop, "signature", filename)

    found_client = find_client_in_db(client_text)

    client_exists = found_client is not None
    amount_exists = verify_amount_in_db(amount_text, found_client)

    if signature_crop is not None:
        signature_result = verify_signature(signature_crop, found_client)
    else:
        signature_result = {
            "is_correct": False,
            "status": "non_detectee",
            "score": 0,
            "template_score": 0,
            "orb_score": 0,
            "message": "Signature non détectée."
        }

    result_image = draw_result_image(image, instances)

    result_filename = "result_" + filename
    result_path = os.path.join(RESULT_FOLDER, result_filename)
    cv2.imwrite(result_path, result_image)

    verification = {
        "client_text_detected": client_text,
        "amount_text_detected": amount_text,
        "client_ollama_result": client_ollama_result,
        "amount_ollama_result": amount_ollama_result,
        "client_exists": client_exists,
        "client": found_client,
        "amount_exists": amount_exists,
        "signature_correct": signature_result["is_correct"],
        "signature_status": signature_result["status"],
        "signature_score": signature_result["score"],
        "signature_template_score": signature_result["template_score"],
        "signature_orb_score": signature_result["orb_score"],
        "signature_message": signature_result["message"]
    }

    return render_template(
        "cheque.html",
        uploaded_image=web_path(image_path),
        result_image=web_path(result_path),
        client_crop=web_path(client_crop_path),
        amount_crop=web_path(amount_crop_path),
        signature_crop=web_path(signature_crop_path),
        detections=detections,
        verification=verification
    )


@app.route("/clients")
def clients():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM clients")
    rows = cursor.fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/add-client", methods=["POST"])
def add_client():
    name = request.form.get("name")
    amount = request.form.get("amount")
    signature = request.files.get("signature")

    if not name or not amount or not signature:
        return jsonify({
            "error": "name, amount and signature are required"
        }), 400

    safe_name = signature.filename.replace("\\", "_").replace("/", "_")
    signature_filename = str(uuid.uuid4()) + "_" + safe_name
    signature_path = os.path.join(SIGNATURE_FOLDER, signature_filename)
    signature.save(signature_path)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO clients (name, amount, signature_path)
        VALUES (?, ?, ?)
    """, (name, amount, signature_path))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Client added successfully",
        "name": name,
        "amount": amount,
        "signature_path": signature_path
    })


@app.route("/ask", methods=["POST"])
def ask_question():
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Request must be JSON"
        }), 400

    data = request.get_json()

    question = data.get("question", "").strip()
    domain = data.get("domain", "").strip()
    k = int(data.get("k", 6))

    if not question:
        return jsonify({
            "success": False,
            "error": "Question is required"
        }), 400

    if not rag_ready:
        return jsonify({
            "success": False,
            "error": "RAG system is not available"
        }), 500

    final_question = question

    if domain:
        final_question = f"""
Domaine demandé:
{domain}

Question:
{question}
"""

    rag_result = ask_rag_with_docs(final_question, k=k)

    response_text = rag_result["answer"]
    retrieved_docs = rag_result["docs"]

    retrieved_sources = format_retrieved_sources_for_api(retrieved_docs)

    auto_evaluation = automatic_rag_evaluation(
        question=final_question,
        answer=response_text,
        retrieved_docs=retrieved_docs
    )

    return jsonify({
        "success": True,
        "response": response_text.strip(),
        "evaluation": auto_evaluation,
        "retrieved_sources": retrieved_sources
    })


@app.route("/analyze-document", methods=["POST"])
def analyze_document():
    if "image" not in request.files:
        return jsonify({
            "success": False,
            "error": "Image is required"
        }), 400

    document_type = request.form.get("document_type", "cheque_tunisie")

    if document_type not in ["cheque_tunisie", "facture", "auto"]:
        return jsonify({
            "success": False,
            "error": "document_type must be cheque_tunisie, facture or auto"
        }), 400

    file = request.files["image"]

    if not file.filename:
        return jsonify({
            "success": False,
            "error": "Empty filename"
        }), 400

    safe_name = file.filename.replace("\\", "_").replace("/", "_")
    filename = f"{uuid.uuid4()}_{safe_name}"
    image_path = os.path.join(UPLOAD_FOLDER, filename)

    file.save(image_path)

    try:
        extraction = extract_multimodal_with_ollama(
            image_path=image_path,
            document_type=document_type
        )

        if extraction.get("error"):
            return jsonify({
                "success": False,
                "error": extraction["error"],
                "raw_extraction": extraction.get("raw", "")
            }), 500

        extracted_data = extraction.get("data", {})

        rag_analysis = ask_rag(f"""
Analyse ce document avec la base RAG.

Type du document:
{document_type}

Données extraites:
{json.dumps(extracted_data, ensure_ascii=False, indent=2)}

Donne:
1. Type du document.
2. Conformité probable.
3. Champs présents.
4. Champs manquants.
5. Risques.
6. Recommandations.
7. Sources/règles utilisées depuis le contexte si disponibles.
""")

        return jsonify({
            "success": True,
            "document_type": document_type,
            "image_path": web_path(image_path),
            "extraction": extracted_data,
            "raw_extraction": extraction.get("raw", ""),
            "rag_analysis": rag_analysis
        })

    except Exception as e:
        print(f"Erreur analyse multimodale: {e}")

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/rebuild-index", methods=["POST"])
def rebuild_index():
    try:
        initialize_rag(force_rebuild=True)

        return jsonify({
            "success": True,
            "message": "Index FAISS reconstruit avec succès."
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "components": {
            "vector_store": vectorstore is not None,
            "retriever": retriever is not None,
            "llm": llm is not None,
            "rag_ready": rag_ready
        },
        "models": {
            "ollama_text_model": OLLAMA_TEXT_MODEL,
            "ollama_vision_model": OLLAMA_VISION_MODEL
        },
        "paths": {
            "base_dir": BASE_DIR,
            "data_dir": DATA_DIR,
            "cheque_data_dir": CHEQUE_DATA_DIR,
            "facture_data_dir": FACTURE_DATA_DIR,
            "vector_index": VECTOR_INDEX_PATH,
            "upload_dir": UPLOAD_FOLDER
        }
    })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )