"""
Chatbot Agent Server — Multi-agent chatbot powered by OpenAI GPT.
Streams responses via SSE for a real-time typing experience.
Run: cd chatbot && python server.py -> http://0.0.0.0:3851
"""
import json
import os
import re
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent
PORT = 3851

# ──────────────────────── Environment ────────────────────────

def _load_env():
    """Load all env vars from .env file."""
    try:
        from dotenv import load_dotenv
        for env_path in [ROOT / ".env", DIR / ".env"]:
            if env_path.exists():
                load_dotenv(env_path, override=True)
                return
    except ImportError:
        pass

    for base in [ROOT, DIR, Path(os.getcwd()).resolve(), Path(os.getcwd()).resolve().parent]:
        env_file = base / ".env"
        if not env_file.is_file():
            continue
        try:
            with open(env_file, encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, val = line.partition("=")
                        key = key.strip()
                        val = val.split("#")[0].strip().strip('"').strip("'")
                        if key and val:
                            os.environ.setdefault(key, val)
            return
        except OSError:
            pass

_load_env()

# ──────────────────────── LLM Clients ────────────────────────

def _get_anthropic_client():
    """Get an Anthropic client instance for Claude API."""
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Add it to .env file.")
    return anthropic.Anthropic(api_key=api_key)


def _get_openai_client():
    """Get an OpenAI client instance (used for RAG embeddings only)."""
    import openai
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Add it to .env file.")
    return openai.OpenAI(api_key=api_key)


def _prepare_anthropic_messages(messages):
    """Prepare messages for Anthropic API (must alternate user/assistant).
    Extracts system messages into a separate string, merges consecutive same-role messages."""
    system_parts = []
    chat_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        elif role in ("user", "assistant"):
            if chat_messages and chat_messages[-1]["role"] == role:
                chat_messages[-1]["content"] += "\n\n" + content
            else:
                chat_messages.append({"role": role, "content": content})
    if chat_messages and chat_messages[0]["role"] != "user":
        chat_messages.insert(0, {"role": "user", "content": "Hello"})
    if not chat_messages:
        chat_messages = [{"role": "user", "content": "Hello"}]
    return "\n\n".join(system_parts), chat_messages

# ──────────────────────── Project Context ────────────────────────

def _load_project_context():
    ctx_file = ROOT / "PROJECT_CONTEXT.md"
    if ctx_file.exists():
        try:
            return ctx_file.read_text(encoding="utf-8")
        except Exception:
            pass
    return ""

def _load_coding_guidelines():
    guidelines_file = ROOT / "coding_guidelines.md"
    if guidelines_file.exists():
        try:
            return guidelines_file.read_text(encoding="utf-8")
        except Exception:
            pass
    return ""

_LIB_FILES = {
    "untitledui": {"catalog": "catalog.json", "tokens": "tokens.json"},
    "metafore": {"catalog": "metafore_catalog.json", "tokens": "metafore_tokens.json"},
}

def _load_design_system(library="untitledui"):
    ds_dir = ROOT / "design_system"
    out = {"tokens": {}, "catalog": {"components": []}}

    libs = list(_LIB_FILES.keys()) if library == "both" else [library if library in _LIB_FILES else "untitledui"]
    all_components = []
    merged_tokens = {}

    for lib in libs:
        files = _LIB_FILES[lib]
        for name in ("tokens", "catalog"):
            p = ds_dir / files[name]
            try:
                if p.exists():
                    with open(p, encoding="utf-8") as f:
                        data = json.load(f)
                    if name == "catalog":
                        comps = data.get("components", []) if isinstance(data, dict) else data
                        for c in comps:
                            c["_library"] = lib
                        all_components.extend(comps)
                    else:
                        if not merged_tokens:
                            merged_tokens = data
                        else:
                            for k, v in data.get("colors", {}).items():
                                merged_tokens.setdefault("colors", {})[f"{k}_{lib}"] = v
            except Exception:
                pass

    out["catalog"] = {"components": all_components}
    out["tokens"] = merged_tokens
    return out

def _build_system_prompt():
    project_ctx = _load_project_context()
    coding_guidelines = _load_coding_guidelines()
    ds = _load_design_system()
    tokens_str = json.dumps(ds.get("tokens", {}), indent=2)[:2000]
    comps = ds.get("catalog", {}).get("components", [])[:25]
    comps_str = json.dumps(comps, indent=2)[:3000]

    guidelines_section = f"\n\n## Coding Guidelines\n{coding_guidelines}\n" if coding_guidelines else ""

    return f"""You are an expert AI assistant for the "Milestone 1 — Design System Agent" project.

## Full Project Context
{project_ctx}

## Design System
### Tokens (colors, spacing, typography):
{tokens_str}

### Component Catalog (available components):
{comps_str}
{guidelines_section}

## Your Capabilities & Personality
- You are friendly, helpful, and VERY concise
- Keep text explanations SHORT (1-3 sentences max)
- When asked to generate or modify UI, output the code immediately with minimal commentary
- For code, always use fenced code blocks with ```jsx tag
- NEVER repeat large blocks of code that haven't changed

## Code Generation Rules — CRITICAL
- Use function components with hooks
- Use Tailwind CSS classes for styling
- Don't use import statements (React/ReactDOM are global)
- ALWAYS end with: root.render(React.createElement(ComponentName));
- Use the design tokens and color palette from the project
- Output ONLY ONE jsx code block per component (unless asked for variants)
- Keep components compact — under 80 lines when possible

## Variant Generation Rules
When asked to generate multiple variants:
- Output each variant as a SEPARATE ```jsx code block
- Label each with a ## heading like: ## Variant 1: Minimal
- Each variant MUST be a complete standalone React component
- Each MUST end with root.render(React.createElement(ComponentName));
- Use DIFFERENT component names for each variant
- Keep each variant compact (under 60 lines)
- Minimal text between variants"""

SYSTEM_PROMPT = _build_system_prompt()

# Lightweight prompt for general chat (no design system data — saves tokens)
CHAT_SYSTEM_PROMPT = """You are a helpful assistant for the "Milestone 1 — Design System Agent" project.
This project is a multi-agent system (4 LangGraph agents: Orchestrator, Discovery, Generator, QA)
that generates React/JSX UI components using the Untitled UI design system and Tailwind CSS.

Be friendly, concise (1-3 sentences). Answer questions about the project architecture,
how the agents work, the tech stack (React 18, LangGraph, OpenAI GPT-4o, Tailwind CSS),
and general development topics. Do NOT generate UI code in this mode — tell the user to
ask you to "generate" or "create" a component if they want UI code."""


def _is_variant_request(message):
    """Fast regex check: does this message ask for multiple variants?"""
    msg_lower = message.lower()
    return (
        ("variant" in msg_lower and any(w in msg_lower for w in ["generate", "create", "make", "build", "show"]))
        or ("variants" in msg_lower)
        or (re.search(r"generate\s+\d+\s+(?:different|style|version)", msg_lower))
    )


def _fast_classify(message):
    """Quick GPT-4o-mini classification: full intent classification in one call.
    Returns 'generate', 'discover', 'review', or 'chat'.
    Variant requests are routed as 'generate' through the full pipeline."""
    # Fast regex check for variant requests — route through pipeline as generate
    if _is_variant_request(message):
        return "generate"

    import openai
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "generate"
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=10,
            temperature=0,
            messages=[
                {"role": "system", "content": (
                    "Classify the user message into exactly one word:\n"
                    "- \"generate\" if the user wants to CREATE, BUILD, GENERATE, MAKE, DESIGN, "
                    "or MODIFY a UI component, page, dashboard, form, table, card, or any visual element. "
                    "Also \"generate\" for: redesign, add dark mode, make responsive, simplify, add animation.\n"
                    "- \"discover\" if the user wants to EXPLORE, LIST, or BROWSE available components or design tokens.\n"
                    "- \"review\" if the user wants to REVIEW, CHECK, or AUDIT existing code.\n"
                    "- \"chat\" if it's a general question, greeting, explanation request, "
                    "or anything NOT about building/modifying UI.\n\n"
                    "Examples:\n"
                    "\"Create a login form\" -> generate\n"
                    "\"Build me a dashboard\" -> generate\n"
                    "\"Make it more minimal\" -> generate\n"
                    "\"What components are available?\" -> discover\n"
                    "\"Review this code\" -> review\n"
                    "\"Hello\" -> chat\n"
                    "\"How does the pipeline work?\" -> chat\n"
                    "\"Thanks!\" -> chat\n"
                    "Respond with ONLY one word."
                )},
                {"role": "user", "content": message},
            ],
        )
        result = (response.choices[0].message.content or "").strip().lower().strip('"').strip("'")
        if "generate" in result:
            return "generate"
        if "discover" in result:
            return "discover"
        if "review" in result:
            return "review"
        return "chat"
    except Exception as e:
        print(f"[chatbot] Classification error: {e}")
        return "generate"


# ──────────────────────── Preview Template ────────────────────────

PREVIEW_HTML_TPL = """<!DOCTYPE html>
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
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: {
            sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
          },
          colors: {
            blue: {
              25: '#F5FAFF', 50: '#EFF8FF', 100: '#D1E9FF', 200: '#B2DDFF',
              300: '#84CAFF', 400: '#53B1FD', 500: '#2E90FA', 600: '#1570EF',
              700: '#175CD3', 800: '#1849A9', 900: '#194185',
            },
            gray: {
              25: '#FCFCFD', 50: '#F9FAFB', 100: '#F2F4F7', 200: '#EAECF0',
              300: '#D0D5DD', 400: '#98A2B3', 500: '#667085', 600: '#475467',
              700: '#344054', 800: '#1D2939', 900: '#101828',
            },
            emerald: {
              25: '#F6FEF9', 50: '#ECFDF3', 100: '#D1FADF', 200: '#A6F4C5',
              300: '#6CE9A6', 400: '#32D583', 500: '#12B76A', 600: '#039855',
              700: '#027A48', 800: '#05603A', 900: '#054F31',
            },
            red: {
              25: '#FFFBFA', 50: '#FEF3F2', 100: '#FEE4E2', 200: '#FECDCA',
              300: '#FDA29B', 400: '#F97066', 500: '#F04438', 600: '#D92D20',
              700: '#B42318', 800: '#912018', 900: '#7A271A',
            },
            amber: {
              25: '#FFFCF5', 50: '#FFFAEB', 100: '#FEF0C7', 200: '#FEDF89',
              300: '#FEC84B', 400: '#FDB022', 500: '#F79009', 600: '#DC6803',
              700: '#B54708', 800: '#93370D', 900: '#7A2E0E',
            },
            purple: { 50: '#F4F3FF', 100: '#EBE9FE', 500: '#7A5AF8', 600: '#6938EF', 700: '#5925DC' },
            indigo: { 50: '#EEF4FF', 100: '#E0EAFF', 500: '#6172F3', 600: '#444CE7', 700: '#3538CD' },
            rose: { 50: '#FFF1F3', 100: '#FFE4E8', 500: '#F63D68', 600: '#E31B54', 700: '#C01048' },
          },
          boxShadow: {
            xs: '0 1px 2px rgba(16,24,40,0.05)',
            sm: '0 1px 3px rgba(16,24,40,0.1), 0 1px 2px rgba(16,24,40,0.06)',
            md: '0 4px 8px -2px rgba(16,24,40,0.1), 0 2px 4px -2px rgba(16,24,40,0.06)',
            lg: '0 12px 16px -4px rgba(16,24,40,0.08), 0 4px 6px -2px rgba(16,24,40,0.03)',
            xl: '0 20px 24px -4px rgba(16,24,40,0.08), 0 8px 8px -4px rgba(16,24,40,0.03)',
          },
          borderRadius: {
            sm: '0.25rem', md: '0.5rem', lg: '0.75rem', xl: '1rem', '2xl': '1.5rem',
          },
        },
      },
    };
  </script>
  <style>
    body { margin: 0; font-family: 'Inter', ui-sans-serif, system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
    #ds-badge { position: fixed; bottom: 8px; right: 8px; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 9999px; letter-spacing: 0.5px; z-index: 9999; pointer-events: none; font-family: Inter, sans-serif; }
    #ds-badge.untitledui { background: rgba(21,112,239,0.1); color: #1570EF; }
    #ds-badge.metafore { background: rgba(127,86,217,0.1); color: #7F56D9; }
    #ds-badge.both { background: rgba(99,102,241,0.1); color: #6366F1; }
  </style>
</head>
<body>
  <div id="root"></div>
  <div id="ds-badge" class="{library_class}">{library_label}</div>
  <script>
    window.__PREVIEW_ERRORS = [];
    window.onerror = function(msg, url, line, col, err) {
      window.__PREVIEW_ERRORS.push({ msg: msg, line: line, col: col });
      try { window.parent.postMessage({ type: 'preview-error', error: msg, line: line }, '*'); } catch(e) {}
    };
  </script>
  <script type="text/babel" data-presets="react">
    const root = ReactDOM.createRoot(document.getElementById('root'));
    try {
      {code}
    } catch (e) {
      window.__PREVIEW_ERRORS.push({ msg: e.message });
      try { window.parent.postMessage({ type: 'preview-error', error: e.message }, '*'); } catch(pe) {}
      root.render(React.createElement('pre', { style: { color: 'red', padding: 16 } }, e.message));
    }
  </script>
</body>
</html>
"""

# ──────────────────────── Generate Functions (Claude) ────────────────────────

def generate_code(prompt):
    """Call Claude Sonnet to generate React/JSX code using design system."""
    _load_env()
    ds = _load_design_system()
    tokens_str = json.dumps(ds.get("tokens", {}), indent=2)[:2000]
    catalog = ds.get("catalog", {})
    comps = catalog.get("components", catalog) if isinstance(catalog, dict) else catalog
    comps_str = json.dumps(comps[:15], indent=2)[:3000]
    system = f"""You are a React UI generator using the Untitled UI design system. Output only a single React function component.
Use Tailwind CSS with Untitled UI patterns. Design tokens: {tokens_str}
Available patterns: {comps_str}
Rules:
- Output ONLY valid JavaScript/JSX. No markdown, no explanation.
- Single function component with PascalCase name.
- Use Tailwind classes for styling (Untitled UI patterns).
- The code will be injected where const root = ReactDOM.createRoot(document.getElementById('root')); already exists.
- Define a function component then call: root.render(React.createElement(ComponentName));
- Do not use imports; React and ReactDOM are global.
- Use realistic sample data (real names, emails, dollar amounts).
- Buttons: bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm px-4 py-2.5 rounded-lg shadow-sm
- Cards: bg-white border border-gray-200 rounded-xl shadow-sm
- Inputs: border border-gray-300 rounded-lg px-3.5 py-2.5 text-sm shadow-sm focus:ring-2 focus:ring-blue-500"""
    try:
        client = _get_anthropic_client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text or ""
        code = text.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].strip() == "```": lines = lines[:-1]
            code = "\n".join(lines)
        return {"code": code}
    except Exception as e:
        return {"error": str(e)}


def generate_variants(prompt, count, keywords):
    """Generate 2 or 3 React UI variants using Claude Sonnet."""
    count = max(2, min(3, int(count)))
    _load_env()
    keywords = list(keywords)[:count] if keywords else []
    while len(keywords) < count:
        keywords.append(f"Variant {len(keywords) + 1}")
    ds = _load_design_system()
    comps = ds.get("catalog", {}).get("components", [])[:15]
    style_desc = " ".join(f"Variant {i+1} ({keywords[i]}): emphasize that style." for i in range(count))
    user_content = f"""Generate exactly {count} different React UI variants for this request. Each variant should match the same prompt but differ in style/approach.

Prompt: {prompt}

Style descriptions: {style_desc}

Output format — use exactly this structure:
## Variant 1: {keywords[0]}
```jsx
// React component code here
```

## Variant 2: {keywords[1]}
```jsx
// React component code here
```
"""
    if count >= 3:
        user_content += f"""
## Variant 3: {keywords[2]}
```jsx
// React component code here
```
"""
    user_content += """
Output ONLY the variants. Each code block must be a single runnable React function component; then root.render(React.createElement(ThatComponent));"""
    system = f"""You are a React UI generator using the Untitled UI design system. Output {count} variants. Use Tailwind CSS.
Design tokens: {json.dumps(ds.get("tokens", {}), indent=2)[:1500]}
Available patterns: {json.dumps(comps, indent=2)[:2000]}
Rules: valid JS/JSX only, no markdown outside the required format. Single function component per variant.
Use root.render(React.createElement(Component)); No imports; React/ReactDOM are global.
Buttons: bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-sm. Cards: bg-white border border-gray-200 rounded-xl shadow-sm."""
    try:
        client = _get_anthropic_client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        text = (response.content[0].text or "").strip()
        variants = []
        pattern = re.compile(r"##\s*Variant\s*\d+\s*:?\s*([^\n]*)\s*```(?:jsx|javascript)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
        for m in pattern.finditer(text):
            label = (m.group(1) or "").strip() or keywords[len(variants)] if len(variants) < len(keywords) else f"Variant {len(variants)+1}"
            code = m.group(2).strip()
            if code:
                variants.append({"code": code, "keywords": label})
            if len(variants) >= count:
                break
        return {"variants": variants[:count]}
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────── MIME Types ────────────────────────

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".jsx": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

# ──────────────────────── Handler ────────────────────────

class Handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"

        if path == "/api/health":
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            self.send_json({"ok": True, "has_api_key": bool(api_key)})
            return

        if path == "/api/catalog":
            try:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                lib = qs.get("library", ["untitledui"])[0]
                data = _load_design_system(lib)
                if not isinstance(data.get("catalog"), dict):
                    data["catalog"] = {"components": data.get("catalog") or []}
                self.send_json(data)
            except Exception:
                self.send_json({"tokens": {}, "catalog": {"components": []}})
            return

        if path == "/" or path == "/index.html":
            self.serve_file(DIR / "index.html", "text/html; charset=utf-8")
            return

        file_path = DIR / path.lstrip("/")
        if file_path.is_file() and file_path.resolve().is_relative_to(DIR.resolve()):
            ext = file_path.suffix.lower()
            content_type = MIME_TYPES.get(ext, "application/octet-stream")
            self.serve_file(file_path, content_type)
            return

        self.send_error(404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"

        if path == "/api/chat/stream":
            self.handle_stream(body)
            return
        if path == "/api/chat":
            self.handle_chat(body)
            return
        if path == "/api/preview":
            self.handle_preview(body)
            return
        if path == "/api/generate":
            self.handle_generate(body)
            return
        if path == "/api/generate-variants":
            self.handle_generate_variants(body)
            return

        self.send_error(404)

    # ── Streaming chat (SSE) ──

    def handle_stream(self, body):
        _load_env()

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_sse_error("Invalid JSON body")
            return

        message = data.get("message", "").strip()
        history = data.get("history", [])
        intent = data.get("intent", "").strip() or message
        library = data.get("library", "untitledui").strip() or "untitledui"

        if not message:
            self.send_sse_error("Message is required")
            return

        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            self.send_sse_error("OPENAI_API_KEY not set. Add it to .env file.")
            return

        # Smart routing: classify on clean intent, pass full message to pipeline
        if os.environ.get("USE_LANGGRAPH", "").lower() == "true":
            workflow = _fast_classify(intent)
            print(f"[chatbot] Classified as: {workflow} (intent: {intent[:80]}, library: {library})")
            if workflow == "chat":
                self._handle_direct_chat(message, history, api_key)
            else:
                self._handle_langgraph_stream(message, history, workflow=workflow, library=library)
            return

        # Fallback: direct Claude streaming (USE_LANGGRAPH=false)
        self._handle_direct_chat(message, history, api_key, use_full_prompt=True)

    def _handle_direct_chat(self, message, history, api_key, use_full_prompt=False):
        """Fast direct GPT-4o-mini response for general chat — no pipeline overhead."""
        import openai
        sys_prompt = SYSTEM_PROMPT if use_full_prompt else CHAT_SYSTEM_PROMPT
        model_name = "gpt-4o" if use_full_prompt else "gpt-4o-mini"

        messages = [{"role": "system", "content": sys_prompt}]
        for h in history[-20:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        # RAG: inject relevant design system context
        try:
            import sys as _sys
            _root = str(ROOT)
            if _root not in _sys.path:
                _sys.path.insert(0, _root)
            from agent.rag import query as rag_query
            rag_context = rag_query(message, k=3)
            if rag_context:
                messages.insert(1, {
                    "role": "system",
                    "content": f"## Relevant Design System Context\n{rag_context}",
                })
        except Exception as rag_err:
            print(f"[chatbot] RAG inject skipped: {rag_err}")

        messages.append({"role": "user", "content": message})

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            oai_key = os.environ.get("OPENAI_API_KEY", "").strip() or api_key
            client = openai.OpenAI(api_key=oai_key)
            stream = client.chat.completions.create(
                model=model_name,
                max_tokens=1500,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    sse = json.dumps({"type": "chunk", "text": delta.content})
                    self.wfile.write(f"data: {sse}\n\n".encode("utf-8"))
                    self.wfile.flush()

            self.wfile.write(b'data: {"type":"done"}\n\n')
            self.wfile.flush()
        except Exception as e:
            error_msg = json.dumps({"type": "error", "error": str(e)})
            try:
                self.wfile.write(f"data: {error_msg}\n\n".encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass

    def _handle_variant_stream(self, message, history):
        """Generate multiple UI variants using Claude Sonnet and stream results via SSE.
        Bypasses the pipeline since the generator prompt restricts to single code blocks."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            # Status: discovery phase
            sse = json.dumps({"type": "status", "text": "Analyzing variant request..."})
            self.wfile.write(f"data: {sse}\n\n".encode("utf-8"))
            self.wfile.flush()

            # Parse variant count and keywords from user message
            count_match = re.search(r"(\d+)\s*(?:different|style)?\s*variants?", message, re.IGNORECASE)
            count = int(count_match.group(1)) if count_match else 2
            count = max(2, min(3, count))

            # Extract keywords from "Variant N: keyword" patterns
            kw_matches = re.findall(r"Variant\s*\d+\s*:\s*([^.]+)", message, re.IGNORECASE)
            keywords = [k.strip() for k in kw_matches[:count]]
            while len(keywords) < count:
                defaults = ["minimal and clean", "bold and colorful", "playful and rounded"]
                keywords.append(defaults[len(keywords)] if len(keywords) < len(defaults) else f"Variant {len(keywords)+1}")

            # Build context from history (last mentioned component)
            last_code = ""
            last_request = ""
            for h in reversed(history[-20:]):
                if h.get("role") == "assistant" and not last_code:
                    code_match = re.search(r"```(?:jsx|javascript)?\s*\n(.*?)```", h.get("content", ""), re.DOTALL)
                    if code_match:
                        last_code = code_match.group(1).strip()
                if h.get("role") == "user" and not last_request:
                    content = h.get("content", "")
                    if any(w in content.lower() for w in ["create", "build", "generate", "make", "design"]):
                        last_request = content
                if last_code and last_request:
                    break

            sse = json.dumps({"type": "status", "text": f"Generating {count} variants with Claude..."})
            self.wfile.write(f"data: {sse}\n\n".encode("utf-8"))
            self.wfile.flush()

            # Build variant prompt
            ds = _load_design_system()
            comps = ds.get("catalog", {}).get("components", [])[:12]
            style_desc = " ".join(f"Variant {i+1} ({keywords[i]}): emphasize that style." for i in range(count))

            user_content = f"Generate exactly {count} different React UI variants.\n\n"
            if last_request:
                user_content += f"Original request: {last_request}\n\n"
            user_content += f"User says: {message}\n\nStyle descriptions: {style_desc}\n\n"
            if last_code:
                user_content += f"Base component to create variants from:\n```jsx\n{last_code[:2000]}\n```\n\n"
            user_content += "Output format — use exactly this structure:\n"
            for i in range(count):
                user_content += f"\n## Variant {i+1}: {keywords[i]}\n```jsx\n// Complete React component here\n```\n"
            user_content += "\nEach code block must be a complete runnable React function component ending with root.render(React.createElement(ComponentName));"

            system = f"""You are a React UI generator using the Untitled UI design system. Output {count} variants. Use Tailwind CSS.
Available patterns: {json.dumps(comps, indent=2)[:2000]}
Rules: valid JSX only, no markdown outside the required format. Single function component per variant.
Use root.render(React.createElement(Component)); No imports; React/ReactDOM are global.
Use DIFFERENT PascalCase component names for each variant (e.g. DashboardMinimal, DashboardBold).
Buttons: bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-sm. Cards: bg-white border border-gray-200 rounded-xl shadow-sm.
Keep each variant under 60 lines. Include realistic sample data."""

            # Stream from Claude
            client = _get_anthropic_client()
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            ) as stream:
                for text in stream.text_stream:
                    sse = json.dumps({"type": "chunk", "text": text})
                    self.wfile.write(f"data: {sse}\n\n".encode("utf-8"))
                    self.wfile.flush()

            self.wfile.write(b'data: {"type":"done"}\n\n')
            self.wfile.flush()

        except Exception as e:
            error_msg = json.dumps({"type": "error", "error": str(e)})
            try:
                self.wfile.write(f"data: {error_msg}\n\n".encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass

    def _handle_langgraph_stream(self, message, history, workflow="", library="untitledui"):
        """Route the request through the LangGraph multi-agent system.
        Passes pre-classified workflow to skip the classify LLM call in the pipeline."""
        import asyncio
        import sys

        root = str(ROOT)
        if root not in sys.path:
            sys.path.insert(0, root)

        from agent.server import run_agent_stream

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        async def _stream():
            try:
                async for event in run_agent_stream(message, history, workflow=workflow, library=library):
                    chunk = json.dumps(event)
                    self.wfile.write(f"data: {chunk}\n\n".encode("utf-8"))
                    self.wfile.flush()
            except Exception as e:
                error_msg = json.dumps({"type": "error", "error": str(e)})
                try:
                    self.wfile.write(f"data: {error_msg}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except Exception:
                    pass

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_stream())
            loop.close()
        except Exception as e:
            error_msg = json.dumps({"type": "error", "error": str(e)})
            try:
                self.wfile.write(f"data: {error_msg}\n\n".encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass

    def send_sse_error(self, msg):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        error = json.dumps({"type": "error", "error": msg})
        self.wfile.write(f"data: {error}\n\n".encode("utf-8"))
        self.wfile.flush()

    # ── Non-streaming chat (OpenAI GPT) ──

    def handle_chat(self, body):
        _load_env()
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        message = data.get("message", "").strip()
        history = data.get("history", [])

        if not message:
            self.send_json({"error": "message required"}, 400)
            return

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in history[-30:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        try:
            client = _get_openai_client()
            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=4096,
                messages=messages,
            )
            text = response.choices[0].message.content or ""
            self.send_json({"content": text})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    # ── Preview ──

    def handle_preview(self, body):
        try:
            data = json.loads(body) if body else {}
            code = (data.get("code") or "").strip()
            library = (data.get("library") or "untitledui").strip()

            code = re.sub(r'^import\s+.*?[;\n]', '', code, flags=re.MULTILINE)
            code = re.sub(
                r'const\s+root\s*=\s*ReactDOM\.createRoot\s*\([^)]*\)\s*;?\s*',
                '', code
            )

            if code and "root.render" not in code:
                for pattern in [
                    r"function\s+([A-Z][a-zA-Z0-9]*)\s*\(",
                    r"const\s+([A-Z][a-zA-Z0-9]*)\s*=\s*(?:\([^)]*\)\s*=>|function)",
                    r"function\s+([a-zA-Z_][a-zA-Z0-9]*)\s*\(",
                ]:
                    m = re.search(pattern, code)
                    if m:
                        name = m.group(1)
                        code = code + "\nroot.render(React.createElement(" + name + "));"
                        break
            escaped = code.replace("\\", "\\\\").replace("</script>", "<\\/script>")
            lib_labels = {"untitledui": "Untitled UI", "metafore": "Metafore", "both": "Untitled UI + Metafore"}
            html = PREVIEW_HTML_TPL.replace("{code}", escaped).replace("{library_class}", library).replace("{library_label}", lib_labels.get(library, "Untitled UI"))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    # ── Generate ──

    def handle_generate(self, body):
        try:
            data = json.loads(body) if body else {}
            prompt = data.get("prompt", "").strip() or "A simple login form."
            result = generate_code(prompt)
            self.send_json(result)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    # ── Generate Variants ──

    def handle_generate_variants(self, body):
        try:
            data = json.loads(body) if body else {}
            prompt = data.get("prompt", "").strip() or "A simple login form."
            count = max(2, min(3, int(data.get("count", 2))))
            keywords = data.get("keywords") or []
            if isinstance(keywords, list):
                keywords = [str(k).strip() for k in keywords[:count]]
            else:
                keywords = []
            result = generate_variants(prompt, count, keywords)
            self.send_json(result)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    # ── Helpers ──

    def serve_file(self, file_path, content_type):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_error(500)

    def send_json(self, obj, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode("utf-8"))

    def log_message(self, fmt, *args):
        if args and "404" in str(args):
            return
        print(f"[chatbot] {fmt % args}" if args else f"[chatbot] {fmt}")


# ──────────────────────── Main ────────────────────────

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    use_langgraph = os.environ.get("USE_LANGGRAPH", "").lower() == "true"
    ant_ok = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    oai_ok = bool(os.environ.get("OPENAI_API_KEY", "").strip())

    print(f"\n  Design System Agent: http://{host}:{PORT}")
    print(f"  Project root:  {ROOT}")
    print(f"  Mode:          {'LangGraph Multi-Agent (4 agents, 6 tools)' if use_langgraph else 'Direct Claude Streaming'}")
    print(f"  Claude key:    {'Loaded' if ant_ok else 'NOT SET - add ANTHROPIC_API_KEY to .env'}")
    print(f"  OpenAI key:    {'Loaded (RAG embeddings)' if oai_ok else 'NOT SET - RAG disabled'}")
    print(f"  LLM:           GPT-4o-mini (classify/chat) + Claude Sonnet (code gen)")
    print(f"  Context:       PROJECT_CONTEXT.md {'found' if (ROOT / 'PROJECT_CONTEXT.md').exists() else 'NOT FOUND'}")
    print(f"  Guidelines:    coding_guidelines.md {'found' if (ROOT / 'coding_guidelines.md').exists() else 'NOT FOUND'}")
    print()

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

    with ThreadedHTTPServer((host, PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down.")
