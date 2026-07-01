import chromadb
import os

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_or_create_collection(name="documents")

def store_chunks(chunks: list[str], embeddings: list[list[float]], document_id: int):
    ids = [f"doc{document_id}_chunk{i}" for i in range(len(chunks))]
    metadatas = [{"document_id": document_id} for _ in chunks]
    collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)

def query_chunks(query_embedding: list[float], document_id: int, n_results: int = 5):
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"document_id": document_id}
    )
    return results["documents"][0] if results["documents"] else []

def delete_chunks(document_id: int):
    results = collection.get(where={"document_id": document_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])

def get_chunks_by_timestamp(document_id: int, timestamp_patterns: list[str]) -> list[str]:
    """Fetch chunks containing any of the given timestamp patterns via text match."""
    seen = set()
    chunks = []
    for pattern in timestamp_patterns:
        results = collection.get(
            where={"document_id": document_id},
            where_document={"$contains": pattern},
        )
        for doc in (results["documents"] or []):
            if doc not in seen:
                seen.add(doc)
                chunks.append(doc)
    return chunks


def get_chunks_near_timestamp(document_id: int, target_seconds: int, window: int = 30) -> list[str]:
    """Find chunks whose timestamps fall within `window` seconds of `target_seconds`.
    Falls back to the single nearest timestamp if nothing is within the window."""
    import re
    results = collection.get(where={"document_id": document_id})
    if not results["documents"]:
        return []

    # Score each chunk by the closest timestamp it contains to the target
    scored = []
    for doc in results["documents"]:
        ts_matches = re.findall(r'\[(\d{1,2}):(\d{2})\]', doc)
        if not ts_matches:
            continue
        min_dist = min(abs(int(m)*60 + int(s) - target_seconds) for m, s in ts_matches)
        scored.append((min_dist, doc))

    if not scored:
        return []

    scored.sort(key=lambda x: x[0])

    # Return chunks within the window, or at least the nearest one
    nearby = [doc for dist, doc in scored if dist <= window]
    if not nearby:
        nearby = [scored[0][1]]
    return nearby