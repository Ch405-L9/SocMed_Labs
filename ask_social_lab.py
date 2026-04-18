#!/usr/bin/env python3
"""
ask_social_lab.py
Query the BADGR social-lab knowledge base. Retrieves relevant chunks
from ChromaDB, then passes them + your question to a local Ollama model.

Usage:
    python3 ask_social_lab.py "What's the pre-flight checklist for a medical client?"
    python3 ask_social_lab.py "Give me the hook lines for the Atlanta Stack Check series"
    python3 ask_social_lab.py --model phi3:mini "What are the Gate 1 criteria?"

Requirements:
    pip install chromadb requests
    Ollama running: ollama serve
    Knowledge base ingested: python3 social_lab_ingest.py
"""

import sys
import json
import argparse
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
import requests

CHROMA_DIR = Path(__file__).parent / ".chroma_db"
COLLECTION_NAME = "social_lab"
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5-coder:7b"   # confirmed installed; swap to phi3:mini or llama3.2:3b once pulled
TOP_K = 5                      # chunks to retrieve


SYSTEM_PROMPT = """You are the BADGR Technologies internal knowledge assistant.
Answer questions using ONLY the context provided below from the BADGR social-lab knowledge base.
If the answer is not in the context, say so clearly — do not guess or hallucinate.
Be direct and concise. Use bullet points when listing steps or items."""


def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
    results = collection.query(query_texts=[query], n_results=top_k)
    chunks = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({"text": doc, "source": meta["source"]})
    return chunks


def ask_ollama(model: str, context: str, question: str) -> str:
    prompt = f"{SYSTEM_PROMPT}\n\n--- CONTEXT ---\n{context}\n--- END CONTEXT ---\n\nQuestion: {question}\n\nAnswer:"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.1, "num_predict": 512},
    }
    response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=120)
    response.raise_for_status()

    answer = ""
    for line in response.iter_lines():
        if line:
            chunk = json.loads(line)
            token = chunk.get("response", "")
            print(token, end="", flush=True)
            answer += token
            if chunk.get("done"):
                break
    print()  # newline after streamed output
    return answer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="+", help="Your question for the knowledge base")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--top-k", type=int, default=TOP_K, help="Chunks to retrieve")
    parser.add_argument("--sources", action="store_true", help="Print source files used")
    args = parser.parse_args()

    question = " ".join(args.question)

    # Check ChromaDB exists
    if not CHROMA_DIR.exists():
        print("ERROR: Knowledge base not found. Run: python3 social_lab_ingest.py")
        sys.exit(1)

    # Check Ollama is running
    try:
        requests.get("http://localhost:11434", timeout=3)
    except requests.ConnectionError:
        print("ERROR: Ollama not running. Start it with: ollama serve")
        sys.exit(1)

    print(f"\nSearching knowledge base for: {question!r}")
    chunks = retrieve(question, args.top_k)

    if args.sources:
        print("\nSources retrieved:")
        for i, c in enumerate(chunks, 1):
            print(f"  {i}. {c['source']}")

    context = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in chunks
    )

    print(f"\nModel: {args.model}\n{'─'*50}")
    ask_ollama(args.model, context, question)
    print('─'*50)


if __name__ == "__main__":
    main()
