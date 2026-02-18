"""
Agent 3: Code Generation

Writes production React/JSX code using discovered components,
design tokens, and coding guidelines.

Uses Claude (Anthropic) for fast, high-quality code generation.
Falls back to OpenAI GPT-4o if ANTHROPIC_API_KEY is not set.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DESIGN_SYSTEM_DIR = ROOT / "design_system"

_tokens_cache = None


def _load_tokens() -> str:
    """Load design tokens from tokens.json and build a compact summary string."""
    global _tokens_cache
    if _tokens_cache is not None:
        return _tokens_cache
    path = DESIGN_SYSTEM_DIR / "tokens.json"
    if not path.exists():
        _tokens_cache = ""
        return _tokens_cache

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    parts = []

    # Color mapping from tailwindMapping
    tw_map = data.get("tailwindMapping", {})
    color_pairs = [f"{k}->{v}" for k, v in tw_map.items() if k != "note"]
    if color_pairs:
        parts.append(f"Color mapping: {', '.join(color_pairs)}")

    # Color families from actual data
    colors = data.get("colors", {})
    if colors:
        families = ", ".join(colors.keys())
        parts.append(f"Color families: {families} (shade ranges 25-900)")

    # Shadows
    shadows = data.get("shadows", {})
    if shadows:
        levels = ", ".join(shadows.keys())
        parts.append(f"Shadows: {levels} (Untitled UI standard)")

    # Border radius
    radius = data.get("radius", {})
    if radius:
        radius_str = ", ".join(f"{k}={v}" for k, v in radius.items())
        parts.append(f"Border radius: {radius_str}")

    # Typography
    typo = data.get("typography", {})
    if typo:
        font = typo.get("fontFamily", {}).get("display", "Inter")
        font_name = font.split(",")[0].strip("' \"")
        weights = "/".join(typo.get("fontWeight", {}).values())
        sizes = "/".join(typo.get("fontSize", {}).keys())
        parts.append(f"Font: {font_name}, weights: {weights}, sizes: {sizes}")

    _tokens_cache = "\n".join(parts)
    return _tokens_cache


def _load_coding_guidelines() -> str:
    """Load coding_guidelines.md content."""
    path = ROOT / "coding_guidelines.md"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            pass
    return ""


def _build_generation_prompt() -> str:
    guidelines = _load_coding_guidelines()
    tokens = _load_tokens()
    guidelines_section = f"\n\n## Coding Guidelines\n{guidelines}" if guidelines else ""

    return f"""You are an expert React UI developer building pixel-perfect components with the Untitled UI design system.

## Design Tokens
{tokens}

## EXACT Untitled UI Tailwind Patterns (COPY THESE EXACTLY)

### Buttons
- Primary: `bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm px-4 py-2.5 rounded-lg shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`
- Secondary: `bg-white hover:bg-gray-50 text-gray-700 font-semibold text-sm px-4 py-2.5 rounded-lg shadow-sm border border-gray-300 transition-colors`
- Destructive: `bg-red-600 hover:bg-red-700 text-white font-semibold text-sm px-4 py-2.5 rounded-lg shadow-sm`
- Ghost: `text-gray-500 hover:text-gray-700 hover:bg-gray-50 text-sm font-medium px-3 py-2 rounded-lg`

### Inputs
- Field: `w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 shadow-sm placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500`
- Label: `block text-sm font-medium text-gray-700 mb-1.5`
- Search: `pl-10 pr-3.5 py-2.5 border border-gray-300 rounded-lg text-sm shadow-sm` (with magnifying glass SVG icon positioned absolute left)

### Cards
- Container: `bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden`
- Header: `px-6 py-5 border-b border-gray-200` with title `text-lg font-semibold text-gray-900`
- Body: `px-6 py-5`
- Stats card: `bg-white border border-gray-200 rounded-xl shadow-sm p-6` with metric `text-3xl font-semibold text-gray-900` and label `text-sm font-medium text-gray-500`

### Tables
- Wrapper: `overflow-hidden border border-gray-200 rounded-xl shadow-sm`
- Table: `min-w-full divide-y divide-gray-200`
- Thead: `bg-gray-50`
- Th: `px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider`
- Tbody: `bg-white divide-y divide-gray-200`
- Tr: `hover:bg-gray-50 transition-colors`
- Td: `px-6 py-4 whitespace-nowrap text-sm text-gray-900`
- Td secondary: `px-6 py-4 whitespace-nowrap text-sm text-gray-500`

### Badges / Status Pills
- Success: `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700`
- Error: `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700`
- Warning: `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700`
- Info: `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700`
- Default: `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700`

### Avatars
- Small: `h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-xs font-semibold text-blue-700`
- Medium: `h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-sm font-semibold text-blue-700`
- With image: `h-10 w-10 rounded-full object-cover`

### Layout
- Page: `min-h-screen bg-gray-50`
- Container: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8`
- Section header: `flex items-center justify-between mb-6`
- Divider: `border-t border-gray-200`

### Typography
- Page title: `text-2xl font-semibold text-gray-900`
- Section title: `text-lg font-semibold text-gray-900`
- Body text: `text-sm text-gray-600`
- Caption: `text-xs text-gray-500`
- Link: `text-sm font-medium text-blue-600 hover:text-blue-700`

### Tabs
- Container: `border-b border-gray-200`
- Active tab: `border-b-2 border-blue-600 text-blue-600 font-semibold text-sm px-4 py-3`
- Inactive tab: `text-gray-500 hover:text-gray-700 text-sm font-medium px-4 py-3`

### Modal / Dialog
- Overlay: `fixed inset-0 bg-gray-900/50 backdrop-blur-sm flex items-center justify-center z-50`
- Panel: `bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 overflow-hidden`
- Header: `px-6 py-5 border-b border-gray-200`
- Footer: `px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3`

### Toggle / Switch
- Track ON: `relative w-11 h-6 bg-blue-600 rounded-full transition-colors`
- Track OFF: `relative w-11 h-6 bg-gray-200 rounded-full transition-colors`
- Thumb: `absolute top-0.5 h-5 w-5 bg-white rounded-full shadow-sm transition-transform` (left-0.5 OFF, left-[22px] ON)

### Icons (inline SVG, 20x20, stroke-based)
- Use: `<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={{1.5}}>`
- Common: Search (magnifying glass), ChevronDown, Plus, X, Check, ArrowUp, ArrowDown, Edit, Trash, Filter

## Code Rules (CRITICAL)
- Function components with React.useState / React.useEffect hooks
- PascalCase component names (e.g. UserDashboard, InvoiceTable)
- Tailwind CSS ONLY — NO inline styles, NO CSS-in-JS, NO styled-components
- NO import statements — React and ReactDOM are global via CDN
- ALWAYS end with: `root.render(React.createElement(ComponentName));`
- Include 5-10 rows of REALISTIC sample data (real names, emails, dollar amounts, dates)
- Use interactive state: search filters, tab switching, sorting, status toggles
- Add hover effects, transitions, and focus:ring states on all interactive elements
- Icons MUST be inline SVGs (fill="none" stroke="currentColor" strokeWidth={{1.5}})
{guidelines_section}

## Output Format
- For SINGLE component requests: Output ONLY a single ```jsx fenced code block. NO explanations before or after.
- For VARIANT requests (user asks for 2-3 variants/versions/styles): Output each variant as a SEPARATE ```jsx code block, each preceded by a ## heading like: ## Variant 1: Label. Use DIFFERENT PascalCase component names per variant. Keep each variant under 60 lines.

The code must be complete and immediately renderable in a browser with React 18 + Tailwind CDN."""


GENERATION_PROMPT = _build_generation_prompt()


_claude_model = None
_openai_model = None


def _get_claude_model():
    """Get a cached Claude model via LangChain if ANTHROPIC_API_KEY is available."""
    global _claude_model
    if _claude_model is not None:
        return _claude_model
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("[generator] No ANTHROPIC_API_KEY found — will use GPT-4o")
        return None
    try:
        from langchain_anthropic import ChatAnthropic
        _claude_model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            anthropic_api_key=api_key,
            max_tokens=8192,
            temperature=0.2,
        )
        print("[generator] Claude Sonnet model initialized OK")
        return _claude_model
    except Exception as e:
        print(f"[generator] Claude init FAILED: {e} — will use GPT-4o")
        return None


def _get_openai_model():
    """Fallback to OpenAI GPT-4o (cached singleton)."""
    global _openai_model
    if _openai_model is not None:
        return _openai_model
    from langchain_openai import ChatOpenAI
    _openai_model = ChatOpenAI(model="gpt-4o", temperature=0.2, max_tokens=4096)
    return _openai_model


async def run_generation(user_request: str, discovery_output: str,
                          previous_code: str = "", qa_feedback: str = "") -> str:
    """Run code generation using Claude (primary) or GPT-4o (fallback).

    Returns the generated code as a string.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    claude = _get_claude_model()
    model = claude or _get_openai_model()
    model_name = "Claude Sonnet" if claude else "GPT-4o (fallback)"
    print(f"[generator] >>> Using {model_name} for code generation")

    prompt_parts = [f"BUILD THIS UI: {user_request}"]

    # Check if this is a variant request
    is_variant = "variant" in user_request.lower() or (
        "different" in user_request.lower() and ("style" in user_request.lower() or "version" in user_request.lower())
    )

    if previous_code and is_variant:
        prompt_parts.append(
            f"\n## BASE COMPONENT (create variants FROM this code):\n```jsx\n{previous_code}\n```\n"
            "Generate 2-3 DIFFERENT style variants of the component above. "
            "Each variant must keep the SAME data and functionality but change the visual style/layout. "
            "Use DIFFERENT component names per variant (e.g. DashboardMinimal, DashboardBold). "
            "Each must be a complete standalone component ending with root.render(React.createElement(Name))."
        )
    elif previous_code:
        prompt_parts.append(
            f"\n## Previously Generated Component (modify THIS code):\n```jsx\n{previous_code}\n```\n"
            "The user wants you to MODIFY the component above. "
            "Keep the same structure/data but apply the requested changes."
        )

    if discovery_output:
        prompt_parts.append(
            f"\n## Untitled UI Components to Use:\n{discovery_output}\n"
            "Use these exact Tailwind patterns."
        )

    if qa_feedback:
        prompt_parts.append(f"\n## QA FEEDBACK (fix these issues):\n{qa_feedback}")

    messages = [
        SystemMessage(content=GENERATION_PROMPT),
        HumanMessage(content="\n".join(prompt_parts)),
    ]

    try:
        result = await model.ainvoke(messages)
        print(f"[generator] >>> {model_name} response OK ({len(result.content)} chars)")
        return result.content
    except Exception as e:
        print(f"[generator] >>> {model_name} FAILED: {e}")
        if claude:
            print("[generator] >>> Falling back to GPT-4o...")
            try:
                fallback = _get_openai_model()
                result = await fallback.ainvoke(messages)
                print(f"[generator] >>> GPT-4o fallback OK ({len(result.content)} chars)")
                return result.content
            except Exception as e2:
                print(f"[generator] >>> GPT-4o fallback also FAILED: {e2}")
                return f"Error generating code: {e2}"
        return f"Error generating code: {e}"
