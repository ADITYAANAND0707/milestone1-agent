"""
RAG (Retrieval-Augmented Generation) module for design system knowledge.

Indexes catalog.json, tokens.json, PROJECT_CONTEXT.md, and coding_guidelines.md
into an in-memory vector store. Provides a query() function that returns the most
relevant chunks for a given user message.

Uses OpenAI embeddings (text-embedding-3-small) via the openai client.
Stores embeddings in a local .npy cache file for fast startup.
Auto-rebuilds the index when source files change (based on file mtime hash).
"""

import hashlib
import json
import logging
import os
import re
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DESIGN_SYSTEM_DIR = ROOT / "design_system"
CACHE_DIR = DESIGN_SYSTEM_DIR / ".rag_cache"

_SOURCE_FILES = [
    DESIGN_SYSTEM_DIR / "catalog.json",
    DESIGN_SYSTEM_DIR / "tokens.json",
    ROOT / "PROJECT_CONTEXT.md",
    ROOT / "coding_guidelines.md",
]

# In-memory store
_chunks: list[dict] = []
_embeddings: np.ndarray | None = None
_last_fingerprint: str | None = None


def _fingerprint() -> str:
    """Hash of source file mtimes — changes when any source file is modified."""
    parts = []
    for f in _SOURCE_FILES:
        try:
            parts.append(f"{f.name}:{f.stat().st_mtime_ns}")
        except OSError:
            parts.append(f"{f.name}:missing")
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def _chunk_catalog() -> list[dict]:
    """Create one chunk per component from catalog.json."""
    path = DESIGN_SYSTEM_DIR / "catalog.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    chunks = []
    for comp in data.get("components", []):
        name = comp.get("name", "Unknown")
        desc = comp.get("description", "")
        props = ", ".join(comp.get("props", []))
        pattern = comp.get("tailwind_pattern", "")
        variants = comp.get("variants", {})
        variants_str = ""
        if variants:
            variants_str = "\nVariants: " + ", ".join(
                f"{k}: {v}" for k, v in variants.items()
            )

        text = (
            f"Component: {name}\n"
            f"Description: {desc}\n"
            f"Props: {props}\n"
            f"Tailwind Pattern: {pattern}"
            f"{variants_str}"
        )
        chunks.append({
            "id": f"component-{name.lower()}",
            "text": text,
            "metadata": {"source": "catalog.json", "type": "component", "name": name},
        })

    layouts = data.get("layout_patterns", {})
    if layouts:
        text = "Layout Patterns:\n" + "\n".join(
            f"- {k}: {v}" for k, v in layouts.items()
        )
        chunks.append({
            "id": "layout-patterns",
            "text": text,
            "metadata": {"source": "catalog.json", "type": "layout"},
        })

    icons = data.get("icon_patterns", {})
    if icons:
        text = "Icon Patterns (inline SVG, stroke-based):\n" + "\n".join(
            f"- {k}: {v}" for k, v in icons.items()
        )
        chunks.append({
            "id": "icon-patterns",
            "text": text,
            "metadata": {"source": "catalog.json", "type": "icons"},
        })

    return chunks


def _chunk_tokens() -> list[dict]:
    """Create chunks from tokens.json grouped by category."""
    path = DESIGN_SYSTEM_DIR / "tokens.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    chunks = []
    categories = ["colors", "typography", "spacing", "radius", "shadows", "tailwindMapping"]
    for cat in categories:
        val = data.get(cat)
        if not val:
            continue
        text = f"Design Tokens — {cat}:\n{json.dumps(val, indent=2)}"
        chunks.append({
            "id": f"tokens-{cat}",
            "text": text,
            "metadata": {"source": "tokens.json", "type": "tokens", "category": cat},
        })
    return chunks


def _chunk_markdown(file_path: Path, source_name: str) -> list[dict]:
    """Split a markdown file into chunks by ## headers."""
    if not file_path.exists():
        return []
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return []

    sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    chunks = []
    for i, section in enumerate(sections):
        section = section.strip()
        if not section or len(section) < 20:
            continue
        if len(section) > 800:
            section = section[:800] + "..."
        chunks.append({
            "id": f"{source_name}-section-{i}",
            "text": section,
            "metadata": {"source": source_name, "type": "documentation", "section": i},
        })
    return chunks


def _build_all_chunks() -> list[dict]:
    """Collect all chunks from all sources."""
    chunks = []
    chunks.extend(_chunk_catalog())
    chunks.extend(_chunk_tokens())
    chunks.extend(_chunk_markdown(ROOT / "PROJECT_CONTEXT.md", "PROJECT_CONTEXT.md"))
    chunks.extend(_chunk_markdown(ROOT / "coding_guidelines.md", "coding_guidelines.md"))
    return chunks


_openai_client = None


def _get_openai_client():
    """Get or create a cached OpenAI client singleton."""
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    import openai
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set — needed for embeddings.")
    _openai_client = openai.OpenAI(api_key=api_key)
    return _openai_client


def _get_embeddings(texts: list[str]) -> np.ndarray:
    """Get OpenAI embeddings for a list of texts."""
    client = _get_openai_client()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return np.array([item.embedding for item in response.data], dtype=np.float32)


def _cosine_similarity(query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between a query vector and document vectors."""
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    doc_norms = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-10)
    return doc_norms @ query_norm


def build_index(force: bool = False) -> None:
    """Build or rebuild the in-memory vector index from source files.

    Skips rebuild if source files haven't changed (unless force=True).
    Caches embeddings to disk to avoid re-embedding on restart.
    """
    global _chunks, _embeddings, _last_fingerprint

    fp = _fingerprint()
    if not force and _embeddings is not None and _last_fingerprint == fp:
        return

    chunks = _build_all_chunks()
    if not chunks:
        return

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_emb = CACHE_DIR / f"embeddings_{fp}.npy"
    cache_ids = CACHE_DIR / f"chunk_ids_{fp}.json"

    # Try loading from cache
    if cache_emb.exists() and cache_ids.exists():
        try:
            cached_ids = json.loads(cache_ids.read_text(encoding="utf-8"))
            current_ids = [c["id"] for c in chunks]
            if cached_ids == current_ids:
                _embeddings = np.load(str(cache_emb))
                _chunks = chunks
                _last_fingerprint = fp
                logger.info("[RAG] Loaded %d cached embeddings", len(chunks))
                return
        except Exception:
            pass

    # Embed all chunks
    texts = [c["text"] for c in chunks]
    logger.info("[RAG] Embedding %d chunks...", len(texts))
    _embeddings = _get_embeddings(texts)
    _chunks = chunks
    _last_fingerprint = fp

    # Cache to disk
    try:
        np.save(str(cache_emb), _embeddings)
        cache_ids.write_text(json.dumps([c["id"] for c in chunks]), encoding="utf-8")
        # Clean old cache files
        for f in CACHE_DIR.glob("embeddings_*.npy"):
            if f.name != cache_emb.name:
                f.unlink(missing_ok=True)
        for f in CACHE_DIR.glob("chunk_ids_*.json"):
            if f.name != cache_ids.name:
                f.unlink(missing_ok=True)
    except Exception:
        pass

    logger.info("[RAG] Indexed %d chunks (in-memory + cached to disk)", len(chunks))


def query(text: str, k: int = 3) -> str:
    """Query the RAG index and return the top-k relevant chunks as formatted text.

    Auto-builds the index if needed. Returns an empty string on failure.
    """
    try:
        build_index()
    except Exception as e:
        logger.warning("[RAG] Index build failed: %s", e)
        return ""

    if _embeddings is None or not _chunks:
        return ""

    try:
        query_emb = _get_embeddings([text])[0]
        scores = _cosine_similarity(query_emb, _embeddings)
        top_indices = np.argsort(scores)[::-1][:min(k, len(_chunks))]
    except Exception as e:
        logger.warning("[RAG] Query failed: %s", e)
        return ""

    parts = []
    for i, idx in enumerate(top_indices, 1):
        if scores[idx] < 0.1:
            continue
        parts.append(f"--- Context {i} ---\n{_chunks[idx]['text']}")

    return "\n\n".join(parts)
