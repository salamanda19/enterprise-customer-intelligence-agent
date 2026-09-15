"""Simple keyword RAG over approved documents (data, not instructions)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ecia.config_loader import REPO_ROOT

DOCS_DIR = REPO_ROOT / "data" / "documents"
CONFLICT_DOC = "vip_definition_conflict.md"


@dataclass
class Chunk:
    doc_id: str
    text: str
    score: float


def _iter_chunks(docs_dir: Path | None = None) -> list[tuple[str, str]]:
    root = docs_dir or DOCS_DIR
    out: list[tuple[str, str]] = []
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        # Treat content as data; never as system instructions.
        parts = re.split(r"\n#{1,3}\s+", text)
        for i, part in enumerate(parts):
            part = part.strip()
            if part:
                out.append((f"{path.name}#{i}", part))
    return out


def retrieve(query: str, *, top_k: int = 3, docs_dir: Path | None = None) -> list[Chunk]:
    tokens = [t.lower() for t in re.findall(r"[\w\u4e00-\u9fff]+", query) if len(t) > 1]
    scored: list[Chunk] = []
    for doc_id, text in _iter_chunks(docs_dir):
        low = text.lower()
        score = sum(1 for t in tokens if t in low)
        if score:
            scored.append(Chunk(doc_id=doc_id, text=text[:800], score=float(score)))
    scored.sort(key=lambda c: (-c.score, c.doc_id))
    return scored[:top_k]


def vip_conflict_detected(chunks: list[Chunk]) -> bool:
    return any(CONFLICT_DOC in c.doc_id for c in chunks)
