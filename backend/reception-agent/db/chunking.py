import json


def chunk_text(text, chunk_size=500, overlap=200):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)

        start = end - overlap  # overlap pour garder contexte

    return chunks


def chunk_documents(input_file="cleaned_data.json"):
    with open(input_file, "r", encoding="utf-8") as f:
        docs = json.load(f)

    all_chunks = []

    for doc in docs:
        chunks = chunk_text(doc["content"])

        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "source": doc["source"],
                "version": doc["version"],
                "chunk_id": i,
                "content": chunk
            })

    return all_chunks