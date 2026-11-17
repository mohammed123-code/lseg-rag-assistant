import os
import time
from dotenv import load_dotenv
from google import genai
from retrieve import retrieve

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = os.getenv("GEMINI_MODEL")
# Price per 1M tokens (check Google's pricing page, set in .env)
PRICE_IN = float(os.getenv("PRICE_IN_PER_M", "0.30"))
PRICE_OUT = float(os.getenv("PRICE_OUT_PER_M", "2.50"))

PROMPT = """You answer questions about LSEG annual reports.
Use ONLY the context below. If the answer is not in the context, reply exactly: "I don't know based on the provided documents."
Be concise.

Context:
{context}

Question: {question}
Answer:"""


def ask(question, k=8):
    start = time.time()
    chunks = retrieve(question, k)
    context = "\n\n".join(
        f"[{c['source']} p.{c['page']}]\n{c['text']}" for c in chunks
    )
    prompt = PROMPT.format(context=context, question=question)

    for attempt in range(4):  # retry on 503 / rate limits
        try:
            r = client.models.generate_content(model=MODEL, contents=prompt)
            break
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)

    u = r.usage_metadata
    tin, tout = u.prompt_token_count, u.candidates_token_count
    return {
        "answer": r.text,
        "sources": sorted({(c["source"], c["page"]) for c in chunks}),
        "latency_s": round(time.time() - start, 2),
        "input_tokens": tin,
        "output_tokens": tout,
        "est_cost_usd": round((tin * PRICE_IN + tout * PRICE_OUT) / 1e6, 6),
    }


if __name__ == "__main__":
    print(ask("What was total revenue in 2025?"))
