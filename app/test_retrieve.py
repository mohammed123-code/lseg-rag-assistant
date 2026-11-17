import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
col = chromadb.PersistentClient(path="chroma_db").get_collection("lseg")

q = "What was total income in 2023?"
res = col.query(query_embeddings=model.encode([q]).tolist(), n_results=5)

for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
    print(meta["source"], "page", meta["page"])
    print(doc[:200].replace("\n", " "), "\n")
