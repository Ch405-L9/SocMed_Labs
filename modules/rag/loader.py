#!/usr/bin/env python3
# [MANIS_EDIT] MANIS RAG Loader
# Scans social-lab/rag_sources/ (and any extra paths you register) for .md / .txt files,
# chunks them, builds an in-memory BM25 + keyword index, and exposes a query() function.
#
# No vector DB required – uses rank_bm25 (pure Python, free, no API key).
# For larger corpora swap the BM25Okapi retriever for ChromaDB or FAISS –
# the query() signature stays identical so nothing else needs to change.
#
# Install: pip install rank_bm25
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None  # [MANIS_EDIT] Graceful degradation – falls back to keyword scan

REPO_ROOT = Path(__file__).resolve().parents[2]  # two levels up from modules/rag/

# [MANIS_EDIT] Default source paths – extend this list to add more corpora
DEFAULT_SOURCE_DIRS: list[Path] = [
    REPO_ROOT / "social-lab" / "rag_sources",
    REPO_ROOT / "social-lab" / "01_brand",
    REPO_ROOT / "social-lab" / "02_research",
    REPO_ROOT / "social-lab" / "04_content_blueprints",
    REPO_ROOT / "EXTRAS&ADDITIONS",
]

CHUNK_SIZE = 400   # words per chunk
CHUNK_OVERLAP = 50  # words of overlap between chunks


# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------

def _chunk_text(text: str, source_id: str) -> list[dict]:
    """Split text into overlapping word-window chunks."""
    words = text.split()
    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    for i in range(0, max(1, len(words) - CHUNK_OVERLAP), step):
        window = words[i : i + CHUNK_SIZE]
        if not window:
            break
        chunks.append({
            "id": f"{source_id}::{i}",
            "source": source_id,
            "text": " ".join(window),
            "start_word": i,
        })
    return chunks


def _load_file(path: Path) -> list[dict]:
    """Read a .md or .txt file and return chunks."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    # [MANIS_EDIT] Strip markdown code fences for cleaner retrieval
    raw = re.sub(r"```[\s\S]*?```", "", raw)
    source_id = str(path.relative_to(REPO_ROOT))
    return _chunk_text(raw, source_id)


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

class RAGIndex:
    """In-memory BM25 index over all registered source files."""

    def __init__(self, source_dirs: list[Path] | None = None):
        self.chunks: list[dict] = []
        self._bm25: Any = None
        self._tokenized: list[list[str]] = []
        self.source_dirs = source_dirs or DEFAULT_SOURCE_DIRS

    def build(self) -> int:
        """Scan source dirs, chunk all files, build index. Returns chunk count."""
        # [MANIS_EDIT] Walk each registered source dir
        for src_dir in self.source_dirs:
            if not src_dir.exists():
                continue
            for path in sorted(src_dir.rglob("*")):
                if path.suffix.lower() in (".md", ".txt") and path.is_file():
                    self.chunks.extend(_load_file(path))

        if not self.chunks:
            return 0

        self._tokenized = [c["text"].lower().split() for c in self.chunks]

        if BM25Okapi:
            self._bm25 = BM25Okapi(self._tokenized)
        return len(self.chunks)

    def query(self, question: str, top_k: int = 5) -> list[dict]:
        """Return top_k most relevant chunks for the question."""
        if not self.chunks:
            return [{"text": "[RAG index is empty. Run build() first.]", "source": "", "score": 0}]

        tokens = question.lower().split()

        if self._bm25:
            # [MANIS_EDIT] BM25 ranking (preferred)
            scores = self._bm25.get_scores(tokens)
            ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        else:
            # [MANIS_EDIT] Fallback: simple keyword hit count
            def _hits(chunk_tokens: list[str]) -> int:
                return sum(1 for t in tokens if t in chunk_tokens)
            ranked = sorted(range(len(self._tokenized)),
                            key=lambda i: _hits(self._tokenized[i]), reverse=True)

        results = []
        for idx in ranked[:top_k]:
            c = self.chunks[idx]
            results.append({
                "source": c["source"],
                "chunk_id": c["id"],
                "text": c["text"],
            })
        return results


# ---------------------------------------------------------------------------
# Module-level singleton (lazy-loaded on first query)
# ---------------------------------------------------------------------------

_INDEX: RAGIndex | None = None


def get_index(force_rebuild: bool = False) -> RAGIndex:
    """Return the shared RAGIndex, building it on first call."""
    global _INDEX
    if _INDEX is None or force_rebuild:
        _INDEX = RAGIndex()
        _INDEX.build()
    return _INDEX


def query(question: str, top_k: int = 5) -> list[dict]:
    """Convenience wrapper – used by mcp_server_rag.py."""
    return get_index().query(question, top_k=top_k)
