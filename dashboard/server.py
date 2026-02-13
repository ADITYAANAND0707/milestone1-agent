"""Dashboard: local catalog + clone library + chat (Claude) + generate + preview. No MCP server required."""
import json
import os
import re
import subprocess
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent

def _load_env_key():
    """Ensure ANTHROPIC_API_KEY is set from .env if not already in os.environ."""
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
DESIGN_SYSTEM_DIR = ROOT / "design_system"
if not DESIGN_SYSTEM_DIR.exists():
    for base in [Path(os.getcwd()).resolve(), Path(os.getcwd()).resolve().parent]:
        candidate = base / "design_system"
        if candidate.exists():
            DESIGN_SYSTEM_DIR = candidate
            break
COMPONENT_LIBRARY = ROOT / "component-library"
PORT = 3850

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


def load_design_system():
    out = {"tokens": {}, "catalog": {"components": []}}
    for name in ("tokens", "catalog"):
        p = DESIGN_SYSTEM_DIR / f"{name}.json"
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


def chat_with_claude(message: str, history: list) -> dict:
    """Send message to Claude; history is list of {role, content}. Returns { content } or { error }."""
    _load_env_key()
    try:
        import anthropic
    except ImportError:
        return {"error": "anthropic not installed. pip install anthropic"}
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return {"error": "Set ANTHROPIC_API_KEY to chat with Claude on this page."}
    ds = load_design_system()
    catalog = ds.get("catalog", {})
    comps = catalog.get("components", []) if isinstance(catalog, dict) else []
    system = "You are a helpful coding assistant. The user is building UI with a design system. When they ask for UI/code, use the component catalog they have: " + json.dumps(comps[:20], indent=2) + ". Prefer React + Tailwind. Be concise."
    messages = []
    for h in history[-20:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            messages=messages,
        )
        text = msg.content[0].text if msg.content else ""
        return {"content": text}
    except Exception as e:
        return {"error": str(e)}


def clone_component_library() -> dict:
    """Run clone script for Untitled UI repo. Returns { ok } or { error }."""
    script = ROOT / "scripts" / "clone-component-library.ps1"
    script_sh = ROOT / "scripts" / "clone-component-library.sh"
    try:
        if os.name == "nt" and script.exists():
            out = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
        elif script_sh.exists():
            out = subprocess.run(
                ["sh", str(script_sh)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
        else:
            # fallback: git clone directly
            if COMPONENT_LIBRARY.exists():
                return {"ok": True, "message": "component-library already exists"}
            out = subprocess.run(
                ["git", "clone", "https://github.com/untitleduico/untitledui-nextjs-starter-kit.git", str(COMPONENT_LIBRARY)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
        if out.returncode != 0:
            return {"error": (out.stderr or out.stdout or "Clone failed")[:500]}
        return {"ok": True, "message": "Component library cloned"}
    except subprocess.TimeoutExpired:
        return {"error": "Clone timed out"}
    except FileNotFoundError:
        return {"error": "git or script not found"}
    except Exception as e:
        return {"error": str(e)}


def generate_code(prompt: str) -> dict:
    """Call Anthropic to generate React/TSX using design system. Returns { code } or { error }."""
    _load_env_key()
    try:
        import anthropic
    except ImportError:
        return {"error": "anthropic package not installed. pip install anthropic"}
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set. Set it in your environment to generate from this page."}
    ds = load_design_system()
    tokens_str = json.dumps(ds.get("tokens", {}), indent=2)
    catalog = ds.get("catalog", {})
    comps = catalog.get("components", catalog) if isinstance(catalog, dict) else catalog
    comps_str = json.dumps(comps, indent=2)
    system = f"""You are a React UI generator. Output only a single React function component that satisfies the user's request.
Use Tailwind CSS classes (via CDN). Use these design tokens for colors/spacing:
{tokens_str}
Available component patterns (use equivalent Tailwind + HTML):
{comps_str}
Rules:
- Output ONLY valid JavaScript/JSX. No markdown, no explanation.
- Use the exact import paths from the catalog (e.g. from '@/components/base/buttons/button') when using those components. For dashboard preview you can also use inline Tailwind-only markup if imports would fail in a standalone snippet.
- Single function component. Use React.createElement or JSX.
- Use Tailwind classes: e.g. className="rounded-lg p-4 bg-white border border-neutral-200".
- Map primary color to blue-500/600, neutral to gray/slate.
- The code will be injected where const root = ReactDOM.createRoot(document.getElementById('root')); already exists. So define a single function component (e.g. function App() { ... }) then call: root.render(React.createElement(App));
- Do not use imports; assume React and ReactDOM are global."""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text if msg.content else ""
        code = text.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines)
        return {"code": code}
    except Exception as e:
        return {"error": str(e)}


def generate_variants(prompt: str, count: int, keywords: list) -> dict:
    """Generate 2 or 3 React UI variants with optional description keywords. Returns { variants: [ { code, keywords } ] } or { error }."""
    count = max(2, min(3, int(count)))
    _load_env_key()
    try:
        import anthropic
    except ImportError:
        return {"error": "anthropic package not installed. pip install anthropic"}
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set. Set it in .env for generate variants."}
    keywords = list(keywords)[:count] if keywords else []
    while len(keywords) < count:
        keywords.append(f"Variant {len(keywords) + 1}")
    ds = load_design_system()
    tokens_str = json.dumps(ds.get("tokens", {}), indent=2)
    catalog = ds.get("catalog", {})
    comps = catalog.get("components", catalog) if isinstance(catalog, dict) else catalog
    comps_str = json.dumps(comps, indent=2)
    style_desc = " ".join(f"Variant {i+1} ({keywords[i]}): emphasize that style." for i in range(count))
    user_content = f"""Generate exactly {count} different React UI variants for this request. Each variant should match the same prompt but differ in style/approach as described.

Prompt: {prompt}

Style descriptions (use these to differentiate): {style_desc}

Output format — use exactly this structure with ## headers and ```jsx code blocks:
## Variant 1: {keywords[0]}
```jsx
// React component code here
```

## Variant 2: {keywords[1]}
```jsx
// React component code here
"""
    if count >= 3:
        user_content += f"""
## Variant 3: {keywords[2]}
```jsx
// React component code here
```
"""
    user_content += """
Output ONLY the variants as above. No other text. Each code block must be a single runnable React function component; then root.render(React.createElement(ThatComponent));"""
    system = f"""You are a React UI generator. Output {count} variants only. Use Tailwind CSS. Design tokens:
{json.dumps(ds.get("tokens", {}), indent=2)}
Available patterns: {json.dumps(comps[:15], indent=2)}
Rules: valid JS/JSX only, no markdown outside the required ## and ``` format. Single function component per variant. Use root.render(React.createElement(Component)); No imports; React/ReactDOM are global."""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system,
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
        if len(variants) < count:
            parts = re.split(r"##\s*Variant\s*\d+", text, flags=re.IGNORECASE)
            for i, part in enumerate(parts[1 : count + 1]):
                if i < len(variants):
                    continue
                code_m = re.search(r"```(?:jsx|javascript)?\s*\n(.*?)```", part, re.DOTALL | re.IGNORECASE)
                if code_m:
                    code = code_m.group(1).strip()
                    if code:
                        variants.append({"code": code, "keywords": keywords[i] if i < len(keywords) else f"Variant {i+1}"})
        return {"variants": variants[:count]}
    except Exception as e:
        return {"error": str(e)}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
        if path == "/api/catalog":
            try:
                data = load_design_system()
                if not isinstance(data.get("catalog"), dict):
                    data["catalog"] = {"components": data.get("catalog") or []}
                self.send_json(data)
            except Exception:
                self.send_json({"tokens": {}, "catalog": {"components": []}})
            return
        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            try:
                with open(DIR / "index.html", "r", encoding="utf-8") as f:
                    html = f.read()
                data = load_design_system()
                catalog = data.get("catalog") or {}
                comps = catalog.get("components", []) if isinstance(catalog, dict) else []
                inject = json.dumps({"catalog": {"components": comps}, "tokens": data.get("tokens", {})})
                html = html.replace("window.__INJECTED_CATALOG__ = null;", "window.__INJECTED_CATALOG__ = " + inject + ";")
            except Exception:
                with open(DIR / "index.html", "rb") as f:
                    html = f.read().decode("utf-8", errors="replace")
            self.wfile.write(html.encode("utf-8"))
            return
        # static file
        file_path = DIR / path.lstrip("/")
        if file_path.is_file() and file_path.resolve().is_relative_to(DIR.resolve()):
            self.send_response(200)
            if path.endswith(".js"):
                self.send_header("Content-Type", "application/javascript")
            elif path.endswith(".css"):
                self.send_header("Content-Type", "text/css")
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
            return
        self.send_error(404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
        if path == "/api/generate":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                data = json.loads(body) if body else {}
                prompt = data.get("prompt", "").strip() or "A simple login form with email and password."
                result = generate_code(prompt)
                self.send_json(result)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return
        if path == "/api/generate-variants":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                data = json.loads(body) if body else {}
                prompt = data.get("prompt", "").strip() or "A simple login form with email and password."
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
            return
        if path == "/api/preview":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
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
            return
        if path == "/api/chat":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                data = json.loads(body) if body else {}
                message = data.get("message", "").strip()
                history = data.get("history", [])
                if not message:
                    self.send_json({"error": "message required"}, 400)
                    return
                result = chat_with_claude(message, history)
                self.send_json(result)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return
        if path == "/api/clone-library":
            try:
                result = clone_component_library()
                self.send_json(result)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return
        self.send_error(404)

    def send_json(self, obj, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode("utf-8"))

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    with HTTPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Dashboard: http://127.0.0.1:{PORT}")
        key_ok = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
        print("Uses local catalog (design_system/) + cloned repo.", end=" ")
        print("ANTHROPIC_API_KEY loaded — chat & generate enabled." if key_ok else "Set ANTHROPIC_API_KEY in .env for chat & generate.")
        httpd.serve_forever()
