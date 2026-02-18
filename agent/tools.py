"""
All 6 LangChain tools for the multi-agent system.

Tools 1-3: Read from design_system/ JSON files (same data as MCP server).
Tools 4-6: Custom Python logic for preview, quality, and accessibility.
"""

import json
import re
from pathlib import Path

from langchain_core.tools import tool

ROOT = Path(__file__).resolve().parent.parent
DESIGN_SYSTEM_DIR = ROOT / "design_system"

# ── Pre-compiled regex patterns (avoid recompilation per call) ──
_RE_FUNC_COMPONENT = re.compile(r"function\s+([a-zA-Z_]\w*)\s*\(")
_RE_CONST_COMPONENT = re.compile(r"const\s+([a-zA-Z_]\w*)\s*=")
_RE_IMPORT = re.compile(r"^import\s+", re.MULTILINE)
_RE_HEX_COLORS = re.compile(r'["\']#[0-9a-fA-F]{3,8}["\']')
_RE_BUTTON_CLASS = re.compile(r'<button[^>]*className="([^"]*)"')
_RE_CARD_CLASS = re.compile(r'className="([^"]*(?:bg-white|card)[^"]*)"', re.IGNORECASE)
_RE_INPUT_CLASS = re.compile(r'<input[^>]*className="([^"]*)"')
_RE_ICON_BUTTON = re.compile(r"<button[^>]*>\s*<(?:svg|img|Icon)", re.IGNORECASE)
_RE_IMG_TAG = re.compile(r"<img[^>]*>", re.IGNORECASE)

# ── Mtime-based JSON cache ──
_json_cache: dict[str, dict] = {}  # {name: {"mtime": float, "data": dict}}


def _load_json(name: str):
    """Load a JSON file from design_system/ with mtime-based caching."""
    path = DESIGN_SYSTEM_DIR / f"{name}.json"
    if not path.exists():
        return {}

    try:
        current_mtime = path.stat().st_mtime
    except OSError:
        return {}

    cached = _json_cache.get(name)
    if cached and cached["mtime"] == current_mtime:
        return cached["data"]

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Build lookup dict for catalog components (O(1) search by name)
    if name == "catalog" and "components" in data:
        data["_lookup"] = {c["name"].lower(): c for c in data["components"]}

    _json_cache[name] = {"mtime": current_mtime, "data": data}
    return data


# ────────────── Tool 1: list_components (MCP equivalent) ──────────────

@tool
def list_components() -> str:
    """List all components in the Untitled UI design system.
    Returns name, description, and props for each of the 24 components."""
    data = _load_json("catalog")
    components = data.get("components", [])
    return json.dumps(components, indent=2)


# ────────────── Tool 2: get_component_spec (MCP equivalent) ──────────────

@tool
def get_component_spec(component_name: str) -> str:
    """Get full specification for one component: all props, description, import path.

    Args:
        component_name: Component name, e.g. Button, Input, Card
    """
    data = _load_json("catalog")
    lookup = data.get("_lookup", {})
    comp = lookup.get(component_name.lower())
    if comp:
        return json.dumps(comp, indent=2)
    available = list(lookup.keys()) if lookup else [c["name"] for c in data.get("components", [])]
    return json.dumps({"error": f"'{component_name}' not found", "available": available})


# ────────────── Tool 3: get_design_tokens (MCP equivalent) ──────────────

@tool
def get_design_tokens() -> str:
    """Get design tokens: colors, typography, spacing, border radius.
    Use these values when writing Tailwind classes in generated code."""
    data = _load_json("tokens")
    return json.dumps(data, indent=2)


# ────────────── Tool 4: preview_component (Custom) ──────────────

PREVIEW_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          fontFamily: {{ sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] }},
          colors: {{
            blue: {{
              25: '#F5FAFF', 50: '#EFF8FF', 100: '#D1E9FF', 200: '#B2DDFF',
              300: '#84CAFF', 400: '#53B1FD', 500: '#2E90FA', 600: '#1570EF',
              700: '#175CD3', 800: '#1849A9', 900: '#194185',
            }},
            gray: {{
              25: '#FCFCFD', 50: '#F9FAFB', 100: '#F2F4F7', 200: '#EAECF0',
              300: '#D0D5DD', 400: '#98A2B3', 500: '#667085', 600: '#475467',
              700: '#344054', 800: '#1D2939', 900: '#101828',
            }},
            emerald: {{
              25: '#F6FEF9', 50: '#ECFDF3', 100: '#D1FADF', 200: '#A6F4C5',
              300: '#6CE9A6', 400: '#32D583', 500: '#12B76A', 600: '#039855',
              700: '#027A48', 800: '#05603A', 900: '#054F31',
            }},
            red: {{
              25: '#FFFBFA', 50: '#FEF3F2', 100: '#FEE4E2', 200: '#FECDCA',
              300: '#FDA29B', 400: '#F97066', 500: '#F04438', 600: '#D92D20',
              700: '#B42318', 800: '#912018', 900: '#7A271A',
            }},
            amber: {{
              25: '#FFFCF5', 50: '#FFFAEB', 100: '#FEF0C7', 200: '#FEDF89',
              300: '#FEC84B', 400: '#FDB022', 500: '#F79009', 600: '#DC6803',
              700: '#B54708', 800: '#93370D', 900: '#7A2E0E',
            }},
            purple: {{ 50: '#F4F3FF', 100: '#EBE9FE', 500: '#7A5AF8', 600: '#6938EF', 700: '#5925DC' }},
            indigo: {{ 50: '#EEF4FF', 100: '#E0EAFF', 500: '#6172F3', 600: '#444CE7', 700: '#3538CD' }},
            rose: {{ 50: '#FFF1F3', 100: '#FFE4E8', 500: '#F63D68', 600: '#E31B54', 700: '#C01048' }},
          }},
          boxShadow: {{
            xs: '0 1px 2px rgba(16,24,40,0.05)',
            sm: '0 1px 3px rgba(16,24,40,0.1), 0 1px 2px rgba(16,24,40,0.06)',
            md: '0 4px 8px -2px rgba(16,24,40,0.1), 0 2px 4px -2px rgba(16,24,40,0.06)',
            lg: '0 12px 16px -4px rgba(16,24,40,0.08), 0 4px 6px -2px rgba(16,24,40,0.03)',
            xl: '0 20px 24px -4px rgba(16,24,40,0.08), 0 8px 8px -4px rgba(16,24,40,0.03)',
          }},
          borderRadius: {{
            sm: '0.25rem', md: '0.5rem', lg: '0.75rem', xl: '1rem', '2xl': '1.5rem',
          }},
        }},
      }},
    }};
  </script>
  <style>
    body {{ margin: 0; font-family: 'Inter', ui-sans-serif, system-ui, sans-serif; -webkit-font-smoothing: antialiased; }}
    #untitled-ui-badge {{ position: fixed; bottom: 8px; right: 8px; background: rgba(21,112,239,0.1); color: #1570EF; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 9999px; letter-spacing: 0.5px; z-index: 9999; pointer-events: none; font-family: Inter, sans-serif; }}
  </style>
</head>
<body>
  <div id="root"></div>
  <div id="untitled-ui-badge">Untitled UI</div>
  <script>
    window.__PREVIEW_ERRORS = [];
    window.onerror = function(msg, url, line, col, err) {{
      window.__PREVIEW_ERRORS.push({{ msg: msg, line: line, col: col }});
      try {{ window.parent.postMessage({{ type: 'preview-error', error: msg, line: line }}, '*'); }} catch(e) {{}}
    }};
  </script>
  <script type="text/babel" data-presets="react">
    const root = ReactDOM.createRoot(document.getElementById('root'));
    try {{
      {code}
    }} catch (e) {{
      window.__PREVIEW_ERRORS.push({{ msg: e.message }});
      try {{ window.parent.postMessage({{ type: 'preview-error', error: e.message }}, '*'); }} catch(pe) {{}}
      root.render(React.createElement('pre', {{ style: {{ color: 'red', padding: 16 }} }}, e.message));
    }}
  </script>
</body>
</html>"""


@tool
def preview_component(code: str) -> str:
    """Render React/JSX code in a sandboxed HTML preview. Saves preview.html and returns status.

    Args:
        code: Complete React/JSX component code (should end with root.render)
    """
    if "root.render" not in code:
        match = _RE_FUNC_COMPONENT.search(code)
        if match:
            code += f"\nroot.render(React.createElement({match.group(1)}));"

    escaped = code.replace("</script>", r"<\/script>")
    html = PREVIEW_TEMPLATE.format(code=escaped)

    preview_path = ROOT / "chatbot" / "preview.html"
    preview_path.write_text(html, encoding="utf-8")

    return json.dumps({
        "status": "ok",
        "preview_path": str(preview_path),
        "message": "Preview generated at chatbot/preview.html",
    })


# ────────────── Tool 5: verify_quality (Custom) ──────────────

@tool
def verify_quality(code: str) -> str:
    """Check generated React code against the team's coding guidelines.
    Returns a structured verdict: PASS or FAIL with score and specific issues.

    Args:
        code: The React/JSX code to review
    """
    issues = []
    score = 100

    # PascalCase component name
    func_match = _RE_FUNC_COMPONENT.search(code)
    if func_match:
        name = func_match.group(1)
        if not name[0].isupper():
            issues.append({"rule": "naming", "severity": "error",
                           "message": f"Component '{name}' must be PascalCase"})
            score -= 15
    else:
        const_match = _RE_CONST_COMPONENT.search(code)
        if const_match and not const_match.group(1)[0].isupper():
            issues.append({"rule": "naming", "severity": "error",
                           "message": "Component name must be PascalCase"})
            score -= 15

    # Tailwind usage
    if "className" not in code:
        issues.append({"rule": "styling", "severity": "warning",
                       "message": "No className found — use Tailwind CSS"})
        score -= 10

    # Inline styles
    if "style={{" in code or "style={" in code:
        issues.append({"rule": "styling", "severity": "warning",
                       "message": "Inline styles detected — prefer Tailwind"})
        score -= 5

    # root.render check
    if "root.render" not in code:
        issues.append({"rule": "structure", "severity": "error",
                       "message": "Missing root.render(React.createElement(Component))"})
        score -= 15

    # Line count
    lines = code.strip().split("\n")
    if len(lines) > 150:
        issues.append({"rule": "structure", "severity": "warning",
                       "message": f"Component is {len(lines)} lines (target: <150)"})
        score -= 5

    # Import statements
    if _RE_IMPORT.search(code):
        issues.append({"rule": "quality", "severity": "error",
                       "message": "Import statements not allowed — React/ReactDOM are global"})
        score -= 10

    # Hardcoded hex colors
    hex_colors = _RE_HEX_COLORS.findall(code)
    if hex_colors:
        issues.append({"rule": "tokens", "severity": "warning",
                       "message": f"Hardcoded colors {hex_colors[:3]} — use Tailwind tokens"})
        score -= 5

    # Class components
    if "class " in code and "extends" in code:
        issues.append({"rule": "quality", "severity": "error",
                       "message": "Class components not allowed — use function components"})
        score -= 15

    # ── Untitled UI Compliance Checks ──

    # Button border-radius: must use rounded-lg (not rounded, rounded-md, rounded-sm)
    button_matches = _RE_BUTTON_CLASS.findall(code)
    for cls in button_matches:
        if "rounded" in cls and "rounded-lg" not in cls and "rounded-full" not in cls:
            issues.append({"rule": "untitled_ui_compliance", "severity": "warning",
                           "message": f"Button uses non-standard border-radius — Untitled UI requires rounded-lg. Found: {cls[:60]}"})
            score -= 5
            break

    # Card border-radius: must use rounded-xl with shadow-sm and border-gray-200
    card_like = _RE_CARD_CLASS.findall(code)
    for cls in card_like:
        if "border" in cls and "rounded" in cls:
            if "rounded-xl" not in cls:
                issues.append({"rule": "untitled_ui_compliance", "severity": "warning",
                               "message": "Card-like element should use rounded-xl (Untitled UI standard)"})
                score -= 5
                break

    # Input border-radius: must use rounded-lg
    input_matches = _RE_INPUT_CLASS.findall(code)
    for cls in input_matches:
        if "rounded" in cls and "rounded-lg" not in cls:
            issues.append({"rule": "untitled_ui_compliance", "severity": "warning",
                           "message": "Input uses non-standard border-radius — Untitled UI requires rounded-lg"})
            score -= 5
            break

    # Color palette check: flag non-Untitled UI colors
    allowed_colors = {"blue", "gray", "emerald", "red", "amber", "purple", "indigo", "rose", "white", "black", "transparent"}
    non_standard = {"teal", "cyan", "lime", "fuchsia", "pink", "orange", "sky", "violet", "slate", "zinc", "stone", "neutral"}
    for bad_color in non_standard:
        if f"-{bad_color}-" in code or f"bg-{bad_color}" in code or f"text-{bad_color}" in code:
            issues.append({"rule": "untitled_ui_compliance", "severity": "warning",
                           "message": f"Non-Untitled UI color '{bad_color}' used — stick to blue/gray/emerald/red/amber/purple/indigo/rose"})
            score -= 5
            break

    # Font override check: should not override Inter
    if "font-family" in code.lower() and "inter" not in code.lower():
        issues.append({"rule": "untitled_ui_compliance", "severity": "warning",
                       "message": "Custom font-family detected — Untitled UI uses Inter"})
        score -= 5

    # Table structure check
    if "<tbody" in code:
        if "divide-y" not in code or "divide-gray" not in code:
            issues.append({"rule": "untitled_ui_compliance", "severity": "warning",
                           "message": "Table tbody should use divide-y divide-gray-200 (Untitled UI pattern)"})
            score -= 5

    score = max(0, score)
    has_errors = any(i["severity"] == "error" for i in issues)
    verdict = "FAIL" if has_errors or score < 70 else "PASS"

    return json.dumps({"verdict": verdict, "score": score, "issues": issues}, indent=2)


# ────────────── Tool 6: check_accessibility (Custom) ──────────────

@tool
def check_accessibility(code: str) -> str:
    """Check React code for accessibility (WCAG AA). Returns verdict and issues.

    Args:
        code: The React/JSX code to check
    """
    issues = []
    score = 100

    # Semantic HTML
    semantic_tags = ["<nav", "<main", "<section", "<header", "<footer",
                     "<article", "<aside", "<form", "<button"]
    has_semantic = any(tag in code for tag in semantic_tags)
    if not has_semantic and len(code.strip().split("\n")) > 10:
        issues.append({"rule": "semantic-html", "severity": "warning",
                       "message": "No semantic HTML elements found"})
        score -= 10

    # Icon-only buttons without aria-label
    if _RE_ICON_BUTTON.search(code):
        if "aria-label" not in code:
            issues.append({"rule": "aria", "severity": "error",
                           "message": "Icon-only button missing aria-label"})
            score -= 15

    # Images without alt
    for img in _RE_IMG_TAG.findall(code):
        if "alt=" not in img:
            issues.append({"rule": "images", "severity": "error",
                           "message": "Image missing alt attribute"})
            score -= 15
            break

    # Form inputs without labels
    if "<input" in code.lower():
        has_label = any(x in code for x in ["<label", "aria-label", "aria-labelledby", "htmlFor"])
        if not has_label:
            issues.append({"rule": "forms", "severity": "error",
                           "message": "Input without associated <label> or aria-label"})
            score -= 15

    # Focus states
    if "className" in code:
        has_focus = any(f in code for f in ["focus:", "focus-visible:", "focus-within:"])
        if not has_focus:
            issues.append({"rule": "focus", "severity": "warning",
                           "message": "No focus state classes — add focus:ring for keyboard nav"})
            score -= 10

    # Low-contrast text
    low_contrast = ["text-gray-200", "text-gray-100", "text-neutral-200", "text-neutral-100"]
    if any(lc in code for lc in low_contrast):
        issues.append({"rule": "contrast", "severity": "warning",
                       "message": "Very light text — may not meet WCAG AA contrast"})
        score -= 5

    score = max(0, score)
    has_errors = any(i["severity"] == "error" for i in issues)
    verdict = "FAIL" if has_errors or score < 70 else "PASS"

    return json.dumps({"verdict": verdict, "score": score, "issues": issues}, indent=2)
