import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from chunking import chunk_documents


def create_faiss_index(
    documents_file="cleaned_data.json",
    index_file="faiss_index.bin",
    metadata_file="documents_metadata.json",
):
    print("Decoupage des documents en chunks...")
    chunks = chunk_documents(documents_file)

    texts = [c["content"] for c in chunks if c.get("content")]
    if not texts:
        raise ValueError("Aucun document valide trouvé pour créer les embeddings.")

    print(f"Creation embeddings pour {len(texts)} chunks...")

    # modèle embedding
    model = SentenceTransformer("all-MiniLM-L6-v2")

    embeddings = model.encode(texts, show_progress_bar=True)

    embeddings = np.array(embeddings).astype("float32")

    # créer index FAISS
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)

    index.add(embeddings)

    print("Index FAISS cree.")

    # sauvegarder index
    faiss.write_index(index, index_file)

    # sauvegarder metadata
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=4)

    print(f"Index sauvegarde dans: {index_file}")
    print(f"Metadata sauvegardee dans: {metadata_file}")