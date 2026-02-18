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

# Cached singletons
_catalog_cache = None
_formatted_prompt_cache = None
_discovery_model = None


def _load_catalog() -> dict:
    """Load catalog.json once and cache it."""
    global _catalog_cache
    if _catalog_cache is not None:
        return _catalog_cache
    path = DESIGN_SYSTEM_DIR / "catalog.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            _catalog_cache = json.load(f)
    else:
        _catalog_cache = {"components": []}
    return _catalog_cache


def _build_catalog_summary() -> str:
    """Build a compact summary of all components with their tailwind patterns."""
    catalog = _load_catalog()
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


_DISCOVERY_TEMPLATE = """You are the component discovery expert for the Untitled UI design system.

## Your Job
Given a user request, pick the relevant components from the catalog below and return
a composition plan with EXACT tailwind classes for each.

## Available Components (24 total)
{catalog}

## Output Format
Return a short composition plan:
- List each needed component with its variant and exact Tailwind classes
- Describe the layout structure
- Be concise — the Generator reads this directly

Example:
"Components needed:
- **Card** (with_header): bg-white border border-gray-200 rounded-xl shadow-sm
- **Table**: w-full, thead bg-gray-50, tbody divide-y divide-gray-200, rows hover:bg-gray-50
- **Badge** success: bg-emerald-50 text-emerald-700 rounded-full
- **Button** primary: bg-blue-600 text-white rounded-lg shadow-sm
Layout: min-h-screen bg-gray-50, max-w-6xl mx-auto px-6 py-8"

Only recommend components from the catalog. Do NOT invent components."""


def _get_formatted_prompt() -> str:
    """Get the discovery system prompt with catalog injected (cached)."""
    global _formatted_prompt_cache
    if _formatted_prompt_cache is not None:
        return _formatted_prompt_cache
    catalog_summary = _build_catalog_summary()
    _formatted_prompt_cache = _DISCOVERY_TEMPLATE.replace("{catalog}", catalog_summary)
    return _formatted_prompt_cache


def _get_discovery_model():
    """Get GPT-4o-mini for fast discovery (cached singleton)."""
    global _discovery_model
    if _discovery_model is not None:
        return _discovery_model
    _discovery_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _discovery_model


async def run_discovery(user_request: str, has_previous_code: bool = False) -> str:
    """Run component discovery as a single direct LLM call.

    Returns the composition plan string.
    """
    model = _get_discovery_model()
    system_prompt = _get_formatted_prompt()

    context = f"Find all relevant Untitled UI components for: {user_request}"
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
