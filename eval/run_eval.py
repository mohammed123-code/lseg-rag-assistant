import json, sys, time, statistics
import requests

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
qs = json.load(open("eval/questions.json", encoding="utf-8"))

def norm(s):
    return s.lower().replace(",", "").replace("’", "'")

rows = []
for i, item in enumerate(qs, 1):
    t = time.time()
    try:
        r = requests.post(f"{URL}/ask", json={"question": item["q"]}, timeout=90).json()
        ans = r.get("answer", "")
        ok = any(norm(m) in norm(ans) for m in item["must_contain"])
        rows.append({"n": i, "type": item["type"], "ok": ok,
                     "latency": r.get("latency_s", round(time.time() - t, 2)),
                     "tin": r.get("input_tokens", 0), "tout": r.get("output_tokens", 0),
                     "cost": r.get("est_cost_usd", 0), "q": item["q"], "ans": ans})
    except Exception as e:
        rows.append({"n": i, "type": item["type"], "ok": False, "latency": 0,
                     "tin": 0, "tout": 0, "cost": 0, "q": item["q"], "ans": f"ERROR {e}"})
    print(i, "PASS" if rows[-1]["ok"] else "FAIL", rows[-1]["q"])
    time.sleep(4)  # stay under free-tier rate limits

lat = sorted(r["latency"] for r in rows)
acc = sum(r["ok"] for r in rows) / len(rows)
summary = (
    f"| Metric | Value |\n|---|---|\n"
    f"| Accuracy | {acc:.0%} ({sum(r['ok'] for r in rows)}/{len(rows)}) |\n"
    f"| Median latency | {statistics.median(lat):.2f} s |\n"
    f"| p95 latency | {lat[int(0.95 * (len(lat) - 1))]:.2f} s |\n"
    f"| Avg input tokens | {statistics.mean(r['tin'] for r in rows):.0f} |\n"
    f"| Avg est. cost / request | ${statistics.mean(r['cost'] for r in rows):.5f} |\n"
)
print("\n" + summary)
open("eval/results.md", "w", encoding="utf-8").write(summary)
json.dump(rows, open("eval/results.json", "w", encoding="utf-8"), indent=2)