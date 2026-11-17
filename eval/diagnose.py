import json, sys
sys.path.insert(0, "app")
from retrieve import retrieve

def norm(s):
    return s.lower().replace(",", "")

qs = json.load(open("eval/questions.json", encoding="utf-8"))
for n in (3, 11, 12):
    item = qs[n - 1]
    print(f"\nQ{n}: {item['q']}")
    for k in (8, 15, 30):
        chunks = retrieve(item["q"], k=k)
        hit = [
            (i + 1, c["source"], c["page"])
            for i, c in enumerate(chunks)
            if any(norm(m) in norm(c["text"]) for m in item["must_contain"])
        ]
        print(f"  k={k}: answer string found in chunks {hit if hit else 'NONE'}")