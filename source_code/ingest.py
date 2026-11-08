import json
import os
import re

import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE" 
os.environ["OMP_NUM_THREADS"] = "1"  
os.environ["TOKENIZERS_PARALLELISM"] = "false"

DOCS_DIR = "docs"
STORE_DIR = "vector_store"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def load_documents(folder):
    docs = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if name.lower().endswith(".txt"):
            with open(path, encoding="utf-8") as f:
                docs.append((name, f.read()))
        elif name.lower().endswith(".pdf"):
            reader = PdfReader(path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            docs.append((name, text))
    return docs


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text = re.sub(r"\s+", " ", text).strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind(". ", start, end)
            if cut > start + size // 2:
                end = cut + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


HEADING_RE = re.compile(r"(?:^|(?<=\s))(\d{1,2})\.\s+((?:[A-Z]{2,}[ ,&/-]*)+)")
MAX_ENTRY_SIZE = 700


def split_sections(text):
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [(None, text)]
    sections = []
    if text[: matches[0].start()].strip():
        sections.append((None, text[: matches[0].start()].strip()))
    for n, m in enumerate(matches):
        end = matches[n + 1].start() if n + 1 < len(matches) else len(text)
        sections.append((m.group(2).strip(" -,&/"), text[m.end():end].strip()))
    return sections


def chunk_document(text):
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    preamble = ""
    for heading, body in split_sections(text):
        if not body:
            continue
        if heading is None and len(body) < 100 and not chunks:
            preamble = body
            continue
        if preamble:
            body, preamble = f"{preamble}. {body}", ""
        entries = [e.strip() for e in re.split(r"(?=\bProblem:)", body) if e.strip()]
        for entry in entries:
            pieces = [entry] if len(entry) <= MAX_ENTRY_SIZE else chunk_text(entry)
            for piece in pieces:
                chunks.append(f"{heading}: {piece}" if heading else piece)
    return chunks


def build_index():
    docs = load_documents(DOCS_DIR)
    if not docs:
        raise SystemExit(f"No .txt or .pdf files found in '{DOCS_DIR}/'")

    records = []
    for name, text in docs:
        for i, chunk in enumerate(chunk_document(text)):
            records.append({"source": name, "chunk_id": i, "text": chunk})
    print(f"Loaded {len(docs)} document(s) -> {len(records)} chunks")

    model = SentenceTransformer(EMBED_MODEL)
    vectors = model.encode(
        [r["text"] for r in records],
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype("float32")

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    os.makedirs(STORE_DIR, exist_ok=True)
    faiss.write_index(index, os.path.join(STORE_DIR, "index.faiss"))
    with open(os.path.join(STORE_DIR, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Saved index with {index.ntotal} vectors to '{STORE_DIR}/'")


if __name__ == "__main__":
    build_index()