#!/usr/bin/env python3
"""
social_lab_ingest.py
Ingests all .md and .yaml files from /social-lab/ into ChromaDB.
Run this after adding or editing any file in the knowledge base.

Usage:
    python3 social_lab_ingest.py
    python3 social_lab_ingest.py --reset   # wipe and rebuild the collection
"""

import os
import sys
import argparse
from pathlib import Path

# pip install chromadb
import chromadb
from chromadb.utils import embedding_functions

SOCIAL_LAB_DIR = Path(__file__).parent / "social-lab"
CHROMA_DIR = Path(__file__).parent / ".chroma_db"
COLLECTION_NAME = "social_lab"
CHUNK_SIZE = 800       # characters per chunk
CHUNK_OVERLAP = 150    # overlap between chunks


def chunk_text(text: str, source: str) -> list[dict]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if chunk.strip():
            chunks.append({
                "id": f"{source}::chunk{idx}",
                "text": chunk,
                "source": source,
            })
        start = end - CHUNK_OVERLAP
        idx += 1
    return chunks


def load_files(base_dir: Path) -> list[dict]:
    """Walk social-lab and load all .md and .yaml files."""
    docs = []
    for ext in ("*.md", "*.yaml", "*.csv"):
        for path in sorted(base_dir.rglob(ext)):
            rel = str(path.relative_to(base_dir.parent))
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
            if not text or text.startswith("# ") and len(text) < 60:
                # skip near-empty stubs
                continue
            for chunk in chunk_text(text, rel):
                docs.append(chunk)
    return docs


def ingest(reset: bool = False):
    print(f"ChromaDB path : {CHROMA_DIR}")
    print(f"Social-lab dir: {SOCIAL_LAB_DIR}")

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Use the built-in all-MiniLM-L6-v2 embedding (no Ollama dependency for embeddings)
    ef = embedding_functions.DefaultEmbeddingFunction()

    if reset and COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)
        print("Existing collection wiped.")

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    docs = load_files(SOCIAL_LAB_DIR)
    if not docs:
        print("No documents found. Check SOCIAL_LAB_DIR path.")
        sys.exit(1)

    print(f"Ingesting {len(docs)} chunks from {SOCIAL_LAB_DIR.name}/ ...")

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        collection.upsert(
            ids=[d["id"] for d in batch],
            documents=[d["text"] for d in batch],
            metadatas=[{"source": d["source"]} for d in batch],
        )
        print(f"  Upserted chunks {i+1}–{min(i+batch_size, len(docs))}")

    print(f"\nDone. Collection '{COLLECTION_NAME}' has {collection.count()} chunks.")
    print("Run ask_social_lab.py to query.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Wipe and rebuild the collection")
    args = parser.parse_args()
    ingest(reset=args.reset)
