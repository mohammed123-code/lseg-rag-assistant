import sys
sys.path.insert(0, "app")
import retrieve as r

q = "What was LSEG's statutory IFRS revenue in 2025?"
# which stored chunks actually contain the figure?
for i, (d, m) in enumerate(zip(r._docs, r._metas)):
    if m["source"] == "lseg_2025.pdf" and "9,081" in d:
        print("contains 9,081:", m["page"], "|", d[:120].replace("\n", " "))

# where does each ranker put them?
tok = r._tok(q)
scores = r._bm25.get_scores(tok)
rank = sorted(range(len(r._ids)), key=lambda i: -scores[i])
for pos, i in enumerate(rank):
    if r._metas[i]["source"] == "lseg_2025.pdf" and "9,081" in r._docs[i]:
        print(f"BM25 rank {pos + 1}, page {r._metas[i]['page']}")
        break