# app/ingest.py
import pymupdf
import tiktoken
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer

DATA_DIR = Path("data")
DB_DIR = "chroma_db"
CHUNK_TOKENS = 500
OVERLAP = 50

enc = tiktoken.get_encoding("cl100k_base")
model = SentenceTransformer("all-MiniLM-L6-v2")


def chunk_text(text):
    tokens = enc.encode(text)
    chunks, start = [], 0
    while start < len(tokens):
        end = start + CHUNK_TOKENS
        chunks.append(enc.decode(tokens[start:end]))
        if end >= len(tokens):
            break
        start = end - OVERLAP
    return chunks


def main():
    client = chromadb.PersistentClient(path=DB_DIR)
    try:
        client.delete_collection("lseg")
    except Exception:
        pass
    col = client.create_collection("lseg", metadata={"hnsw:space": "cosine"})

    ids, docs, metas = [], [], []
    for pdf in sorted(DATA_DIR.glob("*.pdf")):
        doc = pymupdf.open(pdf)
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            if len(text) < 50:
                continue
            for i, chunk in enumerate(chunk_text(text)):
                ids.append(f"{pdf.stem}-p{page_num}-c{i}")
                docs.append(chunk)
                metas.append({"source": pdf.name, "page": page_num})
        print(f"Read {pdf.name}: {len(doc)} pages")

    print(f"Embedding {len(docs)} chunks...")
    embeddings = model.encode(docs, batch_size=64, show_progress_bar=True).tolist()

    for i in range(0, len(docs), 500):
        col.add(
            ids=ids[i:i + 500],
            documents=docs[i:i + 500],
            embeddings=embeddings[i:i + 500],
            metadatas=metas[i:i + 500],
        )
    print(f"Done. Stored {col.count()} chunks.")


if __name__ == "__main__":
    main()
