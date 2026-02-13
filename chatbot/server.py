"""
Chatbot Agent Server — ChatGPT-style chatbot with full project context.
Streams responses via SSE for a real-time typing experience.
Run: cd chatbot && python server.py → http://0.0.0.0:3851
"""
import json
import os
import re
import traceback
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent
PORT = 3851

# ──────────────────────── Environment ────────────────────────

def _load_env_key():
    """Load ANTHROPIC_API_KEY from .env files if not already in environment."""
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return
    for base in [ROOT, DIR, Path(os.getcwd()).resolve(), Path(os.getcwd()).resolve().parent]:
        env_file = base / ".env"
        if not env_file.is_file():
            continue
        try:
            with open(env_file, encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY=") and not line.startswith("ANTHROPIC_API_KEY=#"):
                        key = line.split("=", 1)[1].split("#")[0].strip().strip('"').strip("'")
                        if key:
                            os.environ["ANTHROPIC_API_KEY"] = key
                            return
        except OSError:
            pass
    try:
        from dotenv import load_dotenv
        for env_path in [ROOT / ".env", DIR / ".env"]:
            if env_path.exists():
                load_dotenv(env_path, override=True)
                break
    except ImportError:
        pass

_load_env_key()

# ──────────────────────── Project Context ────────────────────────

def _load_project_context():
    """Load PROJECT_CONTEXT.md content."""
    ctx_file = ROOT / "PROJECT_CONTEXT.md"
    if ctx_file.exists():
        try:
            return ctx_file.read_text(encoding="utf-8")
        except Exception:
            pass
    return ""

def _load_design_system():
    """Load design system catalog and tokens."""
    ds_dir = ROOT / "design_system"
    out = {"tokens": {}, "catalog": {"components": []}}
    for name in ("tokens", "catalog"):
        p = ds_dir / f"{name}.json"
        try:
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                    out[name] = data if isinstance(data, dict) else {"components": data} if name == "catalog" else data
            if name == "catalog" and "components" not in out.get("catalog", {}):
                out.setdefault("catalog", {})["components"] = []
        except Exception:
            pass
    return out

def _build_system_prompt():
    """Build the system prompt with full project context."""
    project_ctx = _load_project_context()
    ds = _load_design_system()
    tokens_str = json.dumps(ds.get("tokens", {}), indent=2)[:2000]
    comps = ds.get("catalog", {}).get("components", [])[:25]
    comps_str = json.dumps(comps, indent=2)[:3000]

    return f"""You are an expert AI assistant for the "Milestone 1 — Design System Agent" project. You have comprehensive knowledge of the entire project, its architecture, codebase, and design system.

## Full Project Context
{project_ctx}

## Design System
### Tokens (colors, spacing, typography):
{tokens_str}

### Component Catalog (available components):
{comps_str}

## Your Capabilities & Personality
- You are friendly, helpful, and VERY concise
- IMPORTANT: Keep text explanations SHORT (1-3 sentences max). Do NOT write long paragraphs explaining the code.
- When asked to generate or modify UI, output the code immediately with minimal commentary
- For code, always use fenced code blocks with ```jsx tag
- NEVER repeat large blocks of code that haven't changed
- When modifying UI, just show the complete updated component — no need to explain every change

## Code Generation Rules — CRITICAL
When writing React components for preview, you MUST follow these rules:
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
- Use DIFFERENT component names for each variant (e.g. CardMinimal, CardBold)
- Keep each variant compact (under 60 lines)
- Minimal text between variants — just the heading and code block"""

SYSTEM_PROMPT = _build_system_prompt()

# ──────────────────────── Preview Template ────────────────────────

PREVIEW_HTML_TPL = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <style> body { margin: 0; font-family: ui-sans-serif, system-ui, sans-serif; } </style>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel" data-presets="react">
    const root = ReactDOM.createRoot(document.getElementById('root'));
    try {
      {code}
    } catch (e) {
      root.render(React.createElement('pre', { style: { color: 'red', padding: 16 } }, e.message));
    }
  </script>
</body>
</html>
"""

# ──────────────────────── Generate Functions ────────────────────────

def generate_code(prompt):
    """Call Anthropic to generate React/JSX code using design system."""
    _load_env_key()
    try:
        import anthropic
    except ImportError:
        return {"error": "anthropic not installed. pip install anthropic"}
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set."}
    ds = _load_design_system()
    tokens_str = json.dumps(ds.get("tokens", {}), indent=2)
    catalog = ds.get("catalog", {})
    comps = catalog.get("components", catalog) if isinstance(catalog, dict) else catalog
    comps_str = json.dumps(comps[:15], indent=2)
    system = f"""You are a React UI generator. Output only a single React function component.
Use Tailwind CSS. Design tokens: {tokens_str}
Available patterns: {comps_str}
Rules:
- Output ONLY valid JavaScript/JSX. No markdown, no explanation.
- Single function component. Use React.createElement or JSX.
- Use Tailwind classes for styling.
- The code will be injected where const root = ReactDOM.createRoot(document.getElementById('root')); already exists.
- Define a function component then call: root.render(React.createElement(ComponentName));
- Do not use imports; React and ReactDOM are global."""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=4096, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text if msg.content else ""
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
    """Generate 2 or 3 React UI variants."""
    count = max(2, min(3, int(count)))
    _load_env_key()
    try:
        import anthropic
    except ImportError:
        return {"error": "anthropic not installed. pip install anthropic"}
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set."}
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
    system = f"""You are a React UI generator. Output {count} variants. Use Tailwind CSS.
Design tokens: {json.dumps(ds.get("tokens", {}), indent=2)[:1500]}
Available patterns: {json.dumps(comps, indent=2)[:2000]}
Rules: valid JS/JSX only, no markdown outside the required format. Single function component per variant. Use root.render(React.createElement(Component)); No imports; React/ReactDOM are global."""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=8192, system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        text = (msg.content[0].text if msg.content else "").strip()
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

        # Health check
        if path == "/api/health":
            api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
            self.send_json({"ok": True, "has_api_key": bool(api_key)})
            return

        # Catalog
        if path == "/api/catalog":
            try:
                data = _load_design_system()
                if not isinstance(data.get("catalog"), dict):
                    data["catalog"] = {"components": data.get("catalog") or []}
                self.send_json(data)
            except Exception:
                self.send_json({"tokens": {}, "catalog": {"components": []}})
            return

        # Serve index.html
        if path == "/" or path == "/index.html":
            self.serve_file(DIR / "index.html", "text/html; charset=utf-8")
            return

        # Static files
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
        _load_env_key()
        try:
            import anthropic
        except ImportError:
            self.send_sse_error("anthropic package not installed. Run: pip install anthropic")
            return

        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            self.send_sse_error("ANTHROPIC_API_KEY not set. Add it to .env file.")
            return

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_sse_error("Invalid JSON body")
            return

        message = data.get("message", "").strip()
        history = data.get("history", [])

        if not message:
            self.send_sse_error("Message is required")
            return

        # Build messages
        messages = []
        for h in history[-30:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        # SSE response headers
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            client = anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                system=SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    chunk = json.dumps({"type": "chunk", "text": text})
                    self.wfile.write(f"data: {chunk}\n\n".encode("utf-8"))
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

    def send_sse_error(self, msg):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        error = json.dumps({"type": "error", "error": msg})
        self.wfile.write(f"data: {error}\n\n".encode("utf-8"))
        self.wfile.flush()

    # ── Non-streaming chat (fallback) ──

    def handle_chat(self, body):
        _load_env_key()
        try:
            import anthropic
        except ImportError:
            self.send_json({"error": "anthropic package not installed. Run: pip install anthropic"}, 500)
            return

        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            self.send_json({"error": "ANTHROPIC_API_KEY not set."}, 400)
            return

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

        messages = []
        for h in history[-30:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        try:
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            text = msg.content[0].text if msg.content else ""
            self.send_json({"content": text})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    # ── Preview ──

    def handle_preview(self, body):
        try:
            data = json.loads(body) if body else {}
            code = (data.get("code") or "").strip()
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
            html = PREVIEW_HTML_TPL.replace("{code}", escaped)
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
        # Quiet logging — only errors
        if args and "404" in str(args):
            return
        print(f"[chatbot] {fmt % args}" if args else f"[chatbot] {fmt}")


# ──────────────────────── Main ────────────────────────

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"\n  Chatbot Agent: http://{host}:{PORT}")
    print(f"  Project root:  {ROOT}")
    key_ok = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    print(f"  API key:       {'Loaded' if key_ok else 'NOT SET — add ANTHROPIC_API_KEY to .env'}")
    print(f"  Context:       PROJECT_CONTEXT.md {'found' if (ROOT / 'PROJECT_CONTEXT.md').exists() else 'NOT FOUND'}")
    print()

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

    with ThreadedHTTPServer((host, PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down.")
