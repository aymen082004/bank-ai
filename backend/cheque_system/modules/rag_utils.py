import os
import json
from typing import Any, List, Dict

import requests
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.language_models.llms import LLM
from langchain_core.documents import Document

from config import (
    CHEQUE_DATA_DIR,
    FACTURE_DATA_DIR,
    VECTOR_INDEX_PATH,
    OLLAMA_URL,
    OLLAMA_TEXT_MODEL
)

from modules.ollama_utils import clean_json_response


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

            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=240
            )

            response.raise_for_status()

            data = response.json()
            return data.get("response", "").strip()

        except requests.exceptions.ConnectionError:
            return "Erreur: Ollama n'est pas lancé. Lancez: ollama serve"

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


vectorstore = None
retriever = None
llm = None
rag_ready = False


def build_vector_index():
    embedding = get_embedding_model()
    raw_docs = load_all_documents()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=180,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    split_docs = splitter.split_documents(raw_docs)

    vs = FAISS.from_documents(split_docs, embedding)
    vs.save_local(VECTOR_INDEX_PATH)

    return vs


def load_or_create_vector_index(force_rebuild=False):
    embedding = get_embedding_model()

    if not force_rebuild and is_valid_faiss_index(VECTOR_INDEX_PATH):
        return FAISS.load_local(
            VECTOR_INDEX_PATH,
            embedding,
            allow_dangerous_deserialization=True
        )

    return build_vector_index()


def initialize_rag(force_rebuild=False):
    global vectorstore, retriever, llm, rag_ready

    vectorstore = load_or_create_vector_index(force_rebuild)
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 10}
    )
    llm = OllamaLLM()
    rag_ready = True


def format_docs(docs):
    parts = []

    for i, doc in enumerate(docs, start=1):
        metadata = doc.metadata or {}

        parts.append(
            f"""
[Document {i}]
Domaine: {metadata.get("domain", "")}
Titre: {metadata.get("title", "")}
Source: {metadata.get("source", "")}
Fichier: {metadata.get("file", "")}

{doc.page_content}
"""
        )

    return "\n\n---\n\n".join(parts)


def get_retrieved_docs(question, k=6):
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


def ask_rag_with_docs(question, k=6):
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
2. Les factures et documents financiers.

Répondez uniquement avec le contexte fourni.

Contexte:
{context}

Question:
{question}

Réponse:
"""

    answer = llm.invoke(prompt)

    return {
        "answer": answer,
        "docs": docs
    }


def ask_rag(question):
    return ask_rag_with_docs(question)["answer"]


def automatic_rag_evaluation(question, answer, retrieved_docs):
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
            "recommendations": []
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

Retourne uniquement un JSON valide:
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
    initialize_rag(False)
except Exception as e:
    rag_ready = False
    print(f"Erreur initialisation RAG: {e}")