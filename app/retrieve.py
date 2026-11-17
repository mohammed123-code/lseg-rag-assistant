import re
import chromadb
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")
_col = chromadb.PersistentClient(path="chroma_db").get_collection("lseg")


def retrieve(question, k=8):
    emb = _model.encode([question]).tolist()
    years = sorted(set(re.findall(r"\b(202[3-5])\b", question)))
    where = None
    if years:
        where = {"source": {"$in": [f"lseg_{y}.pdf" for y in years]}}
    res = _col.query(query_embeddings=emb, n_results=k, where=where)
    return [
        {"text": d, "source": m["source"], "page": m["page"]}
        for d, m in zip(res["documents"][0], res["metadatas"][0])
    ]