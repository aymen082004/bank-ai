import sys
import json
import os
from typing import List, Dict
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# === SHARED RAG STATE ===
GLOBAL_EMBEDDER = None
GLOBAL_FAISS = None
GLOBAL_METADATA = []

def init_rag():
    global GLOBAL_EMBEDDER, GLOBAL_FAISS, GLOBAL_METADATA
    if GLOBAL_EMBEDDER is not None:
        return
    
    try:
        print("[RAG_ENGINE] Étape 1: Chargement de SentenceTransformer (all-MiniLM-L6-v2)...", file=sys.stderr)
        GLOBAL_EMBEDDER = SentenceTransformer('all-MiniLM-L6-v2')
        print("[RAG_ENGINE] SentenceTransformer chargé avec succès !", file=sys.stderr)
        
        # Get the absolute path to the data directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "data")
        
        print(f"[RAG_ENGINE] Étape 2: Chargement de l'index FAISS depuis {data_dir}...", file=sys.stderr)
        index_path = os.path.join(data_dir, "faiss_index.bin")
        if os.path.exists(index_path):
            GLOBAL_FAISS = faiss.read_index(index_path)
            print(f"[RAG_ENGINE] Index FAISS chargé ({GLOBAL_FAISS.ntotal} vecteurs)", file=sys.stderr)
        
        meta_path = os.path.join(data_dir, "documents_metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                GLOBAL_METADATA = json.load(f)
            print(f"[RAG_ENGINE] Métadonnées chargées ({len(GLOBAL_METADATA)} entrées)", file=sys.stderr)
            
    except Exception as e:
        print(f"[RAG_ENGINE ERROR] Impossible d'initialiser RAG : {e}", file=sys.stderr)

def retrieve_context(query: str, top_k: int = 5) -> List[Dict[str, str]]:
    init_rag()
    if not GLOBAL_FAISS or not GLOBAL_EMBEDDER:
        return []
    try:
        # Encodage de la requête
        emb = GLOBAL_EMBEDDER.encode([query]).astype("float32")
        dist, idxs = GLOBAL_FAISS.search(emb, top_k)
        results = []
        for i, idx in enumerate(idxs[0]):
            d = dist[0][i]
            if idx != -1 and idx < len(GLOBAL_METADATA):
                # SEUIL TRÈS LARGE (2.2) pour le débug
                if d < 2.2:
                    item = GLOBAL_METADATA[idx]
                    # LOG DE DEBUG VISIBLE DANS LA CONSOLE
                    print(f"[RAG_ENGINE] MATCH: {item.get('source')} | Score: {d:.3f}", file=sys.stderr)
                    
                    content = item['content']
                    source = item.get('source', 'Document inconnu')
                    
                    # On garde un peu plus de contexte pour l'IA
                    if len(content) > 8000:
                        content = content[:8000] + "..."
                    
                    results.append({
                        "id": f"Source {len(results)+1}",
                        "content": content,
                        "source": source,
                        "distance": float(d)
                    })
        return results
    except Exception as e:
        print(f"[RAG_ENGINE] Erreur retrieve_context: {e}", file=sys.stderr)
        return []

# Auto-init if called
if __name__ == "__main__":
    init_rag()
