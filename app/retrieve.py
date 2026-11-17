import re
import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")
_col = chromadb.PersistentClient(path="chroma_db").get_collection("lseg")

# Load all chunks once at startup for keyword search (about 1,700 chunks, tiny)
_all = _col.get(include=["documents", "metadatas"])
_ids, _docs, _metas = _all["ids"], _all["documents"], _all["metadatas"]
_by_id = {i: (d, m) for i, d, m in zip(_ids, _docs, _metas)}


def _tok(text):
    return re.findall(r"\w+", text.lower())


_bm25 = BM25Okapi([_tok(d) for d in _docs])


def retrieve(question, k=8, pool=30):
    years = sorted(set(re.findall(r"\b(202[3-5])\b", question)))
    allowed = {f"lseg_{y}.pdf" for y in years} if years else None
    where = {"source": {"$in": list(allowed)}} if allowed else None

    # 1) vector search
    emb = _model.encode([question]).tolist()
    vec_ids = _col.query(query_embeddings=emb, n_results=pool, where=where)["ids"][0]

    # 2) keyword search, same year filter
    scores = _bm25.get_scores(_tok(question))
    order = sorted(
        (i for i in range(len(_ids)) if allowed is None or _metas[i]["source"] in allowed),
        key=lambda i: -scores[i],
    )[:pool]
    bm_ids = [_ids[i] for i in order]

    # 3) reciprocal rank fusion
    fused = {}
    for ranking in (vec_ids, bm_ids):
        for rank, cid in enumerate(ranking):
            fused[cid] = fused.get(cid, 0) + 1 / (60 + rank)
    top = sorted(fused, key=fused.get, reverse=True)[:k]

    return [
        {"text": _by_id[c][0], "source": _by_id[c][1]["source"], "page": _by_id[c][1]["page"]}
        for c in top
    ]