import chromadb

CHROMA_DB_PATH = "./chroma_db"

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