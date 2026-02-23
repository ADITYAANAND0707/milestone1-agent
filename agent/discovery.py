"""
Agent 2: Component Discovery

Finds relevant UI components from the Untitled UI library (24 components)
and design tokens for a given user request.

OPTIMIZED: Single direct LLM call with pre-loaded catalog (no ReAct tool loops).
M2 mapping: Ctrlagent Maker agent with Integration tools
"""

import json
import logging
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DESIGN_SYSTEM_DIR = ROOT / "design_system"

_LIB_FILES = {
    "untitledui": "catalog.json",
    "metafore": "metafore_catalog.json",
}

_catalog_cache: dict[str, dict] = {}
_formatted_prompt_cache: dict[str, str] = {}
_discovery_model = None


def _load_catalog(library: str = "untitledui") -> dict:
    """Load catalog JSON for the given library (cached per library)."""
    if library == "both":
        merged = {"components": []}
        for lib in ("untitledui", "metafore"):
            cat = _load_catalog(lib)
            merged["components"].extend(cat.get("components", []))
            for k in ("layout_patterns", "icon_patterns"):
                if cat.get(k):
                    merged.setdefault(k, {}).update(cat[k])
        return merged

    if library in _catalog_cache:
        return _catalog_cache[library]
    fname = _LIB_FILES.get(library, "catalog.json")
    path = DESIGN_SYSTEM_DIR / fname
    if path.exists():
        with open(path, encoding="utf-8") as f:
            _catalog_cache[library] = json.load(f)
    else:
        _catalog_cache[library] = {"components": []}
    return _catalog_cache[library]


def _build_catalog_summary(library: str = "untitledui") -> str:
    """Build a compact summary of all components with their tailwind patterns."""
    catalog = _load_catalog(library)
    parts = []
    for comp in catalog.get("components", []):
        name = comp.get("name", "")
        desc = comp.get("description", "")
        pattern = comp.get("tailwind_pattern", "")
        variants = comp.get("variants", {})
        variants_str = ""
        if variants:
            variants_str = " | Variants: " + ", ".join(variants.keys())
        parts.append(f"**{name}**: {desc}\n  Pattern: {pattern}{variants_str}")

    layouts = catalog.get("layout_patterns", {})
    if layouts:
        parts.append("\n**Layout Patterns**: " + ", ".join(
            f"{k}: {v}" for k, v in layouts.items()
        ))

    return "\n\n".join(parts)


_DISCOVERY_TEMPLATE = """You are the component discovery expert for the {lib_label} design system.

## Your Job
Given a user request, pick the relevant components from the catalog below and return
a composition plan with EXACT tailwind classes for each.

## Available Components
{catalog}

## Output Format
Return a short composition plan:
- List each needed component with its variant and exact Tailwind classes
- Describe the layout structure
- Be concise — the Generator reads this directly

Only recommend components from the catalog. Do NOT invent components."""


def _get_formatted_prompt(library: str = "untitledui") -> str:
    """Get the discovery system prompt with catalog injected (cached per library)."""
    if library in _formatted_prompt_cache:
        return _formatted_prompt_cache[library]
    catalog_summary = _build_catalog_summary(library)
    lib_label = {"untitledui": "Untitled UI", "metafore": "Metafore", "vernam": "Vernam", "both": "Untitled UI + Metafore"}.get(library, library)
    prompt = _DISCOVERY_TEMPLATE.replace("{catalog}", catalog_summary).replace("{lib_label}", lib_label)
    _formatted_prompt_cache[library] = prompt
    return prompt


def _get_discovery_model():
    """Get GPT-4o-mini for fast discovery (cached singleton)."""
    global _discovery_model
    if _discovery_model is not None:
        return _discovery_model
    _discovery_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _discovery_model


async def run_discovery(user_request: str, has_previous_code: bool = False, library: str = "untitledui") -> str:
    """Run component discovery as a single direct LLM call.

    Returns the composition plan string.
    """
    model = _get_discovery_model()
    system_prompt = _get_formatted_prompt(library)
    lib_label = {"untitledui": "Untitled UI", "metafore": "Metafore", "vernam": "Vernam", "both": "Untitled UI + Metafore"}.get(library, library)

    context = f"Find all relevant {lib_label} components for: {user_request}"
    if has_previous_code:
        context += ("\n\nNote: The user is modifying an existing component. "
                    "Include the same components plus any new ones needed.")

    try:
        result = await model.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=context),
        ])
        return result.content
    except Exception as e:
        logger.error("[discovery] LLM call failed: %s", e)
        return f"Discovery failed: {e}"
