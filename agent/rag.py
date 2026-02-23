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

_LIB_FILES = {
    "untitledui": {"catalog": "catalog.json", "tokens": "tokens.json"},
    "metafore": {"catalog": "metafore_catalog.json", "tokens": "metafore_tokens.json"},
}

_COMMON_FILES = [
    ROOT / "PROJECT_CONTEXT.md",
    ROOT / "coding_guidelines.md",
]

# Per-library in-memory stores
_stores: dict[str, dict] = {}  # {lib: {"chunks": [...], "embeddings": ndarray, "fingerprint": str}}


def _fingerprint(library: str = "untitledui") -> str:
    """Hash of source file mtimes — changes when any source file is modified."""
    parts = []
    libs = list(_LIB_FILES.keys()) if library == "both" else [library if library in _LIB_FILES else "untitledui"]
    for lib in libs:
        files = _LIB_FILES[lib]
        for fname in files.values():
            f = DESIGN_SYSTEM_DIR / fname
            try:
                parts.append(f"{f.name}:{f.stat().st_mtime_ns}")
            except OSError:
                parts.append(f"{f.name}:missing")
    for f in _COMMON_FILES:
        try:
            parts.append(f"{f.name}:{f.stat().st_mtime_ns}")
        except OSError:
            parts.append(f"{f.name}:missing")
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def _chunk_catalog(library: str = "untitledui") -> list[dict]:
    """Create one chunk per component from the catalog JSON for the given library."""
    libs = list(_LIB_FILES.keys()) if library == "both" else [library if library in _LIB_FILES else "untitledui"]
    all_chunks = []
    for lib in libs:
        fname = _LIB_FILES[lib]["catalog"]
        all_chunks.extend(_chunk_single_catalog(DESIGN_SYSTEM_DIR / fname, lib))
    return all_chunks


def _chunk_single_catalog(path: Path, lib_name: str) -> list[dict]:
    """Create chunks from a single catalog JSON file."""
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
            f"Component ({lib_name}): {name}\n"
            f"Description: {desc}\n"
            f"Props: {props}\n"
            f"Tailwind Pattern: {pattern}"
            f"{variants_str}"
        )
        chunks.append({
            "id": f"{lib_name}-component-{name.lower()}",
            "text": text,
            "metadata": {"source": path.name, "type": "component", "name": name, "library": lib_name},
        })

    layouts = data.get("layout_patterns", {})
    if layouts:
        text = f"Layout Patterns ({lib_name}):\n" + "\n".join(
            f"- {k}: {v}" for k, v in layouts.items()
        )
        chunks.append({
            "id": f"{lib_name}-layout-patterns",
            "text": text,
            "metadata": {"source": path.name, "type": "layout", "library": lib_name},
        })

    icons = data.get("icon_patterns", {})
    if icons:
        text = f"Icon Patterns ({lib_name}, inline SVG, stroke-based):\n" + "\n".join(
            f"- {k}: {v}" for k, v in icons.items()
        )
        chunks.append({
            "id": f"{lib_name}-icon-patterns",
            "text": text,
            "metadata": {"source": path.name, "type": "icons", "library": lib_name},
        })

    return chunks


def _chunk_tokens(library: str = "untitledui") -> list[dict]:
    """Create chunks from tokens JSON grouped by category."""
    libs = list(_LIB_FILES.keys()) if library == "both" else [library if library in _LIB_FILES else "untitledui"]
    all_chunks = []
    for lib in libs:
        fname = _LIB_FILES[lib]["tokens"]
        path = DESIGN_SYSTEM_DIR / fname
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        categories = ["colors", "typography", "spacing", "radius", "shadows", "tailwindMapping"]
        for cat in categories:
            val = data.get(cat)
            if not val:
                continue
            text = f"Design Tokens ({lib}) — {cat}:\n{json.dumps(val, indent=2)}"
            all_chunks.append({
                "id": f"{lib}-tokens-{cat}",
                "text": text,
                "metadata": {"source": fname, "type": "tokens", "category": cat, "library": lib},
            })
    return all_chunks


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


def _build_all_chunks(library: str = "untitledui") -> list[dict]:
    """Collect all chunks from all sources for the given library."""
    chunks = []
    chunks.extend(_chunk_catalog(library))
    chunks.extend(_chunk_tokens(library))
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


def build_index(force: bool = False, library: str = "untitledui") -> None:
    """Build or rebuild the in-memory vector index from source files.

    Skips rebuild if source files haven't changed (unless force=True).
    Caches embeddings to disk to avoid re-embedding on restart.
    """
    store = _stores.get(library, {})
    fp = _fingerprint(library)

    if not force and store.get("embeddings") is not None and store.get("fingerprint") == fp:
        return

    chunks = _build_all_chunks(library)
    if not chunks:
        return

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_emb = CACHE_DIR / f"embeddings_{library}_{fp}.npy"
    cache_ids = CACHE_DIR / f"chunk_ids_{library}_{fp}.json"

    if cache_emb.exists() and cache_ids.exists():
        try:
            cached_ids = json.loads(cache_ids.read_text(encoding="utf-8"))
            current_ids = [c["id"] for c in chunks]
            if cached_ids == current_ids:
                _stores[library] = {
                    "chunks": chunks,
                    "embeddings": np.load(str(cache_emb)),
                    "fingerprint": fp,
                }
                logger.info("[RAG] Loaded %d cached embeddings for %s", len(chunks), library)
                return
        except Exception:
            pass

    texts = [c["text"] for c in chunks]
    logger.info("[RAG] Embedding %d chunks for %s...", len(texts), library)
    embeddings = _get_embeddings(texts)
    _stores[library] = {"chunks": chunks, "embeddings": embeddings, "fingerprint": fp}

    try:
        np.save(str(cache_emb), embeddings)
        cache_ids.write_text(json.dumps([c["id"] for c in chunks]), encoding="utf-8")
    except Exception:
        pass

    logger.info("[RAG] Indexed %d chunks for %s (in-memory + cached)", len(chunks), library)


def query(text: str, k: int = 3, library: str = "untitledui") -> str:
    """Query the RAG index and return the top-k relevant chunks as formatted text.

    Auto-builds the index if needed. Returns an empty string on failure.
    """
    try:
        build_index(library=library)
    except Exception as e:
        logger.warning("[RAG] Index build failed: %s", e)
        return ""

    store = _stores.get(library, {})
    embeddings = store.get("embeddings")
    chunks = store.get("chunks", [])

    if embeddings is None or not chunks:
        return ""

    try:
        query_emb = _get_embeddings([text])[0]
        scores = _cosine_similarity(query_emb, embeddings)
        top_indices = np.argsort(scores)[::-1][:min(k, len(chunks))]
    except Exception as e:
        logger.warning("[RAG] Query failed: %s", e)
        return ""

    parts = []
    for i, idx in enumerate(top_indices, 1):
        if scores[idx] < 0.1:
            continue
        parts.append(f"--- Context {i} ---\n{chunks[idx]['text']}")

    return "\n\n".join(parts)
