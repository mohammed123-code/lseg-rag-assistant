import json
import time
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from llm import ask  # loads the embedding model once, at startup

app = FastAPI(title="LSEG RAG Assistant")

LOG_FILE = Path("logs/requests.jsonl")
LOG_FILE.parent.mkdir(exist_ok=True)
STATIC_DIR = Path(__file__).parent / "static"

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")

class Question(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


@app.get("/health")
def health():
    return {"status": "ok"}



@app.post("/ask")
def ask_endpoint(body: Question):
    try:
        result = ask(body.question)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    result["sources"] = [{"source": s, "page": p} for s, p in result["sources"]]

    with LOG_FILE.open("a") as f:
        f.write(json.dumps({"ts": time.time(), "question": body.question, **result}) + "\n")
    return result