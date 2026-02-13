# Full Project Context — Milestone 1 Design System Agent

**Use this file when handing off to a different Cursor agent or new session.** It describes the project, structure, how to run it, and important behavior so work can continue without re-discovering the codebase.

---

## 1. What This Project Is

- **Name:** Milestone 1 — Design System Agent  
- **Purpose:** Generate UI (React/JSX) from prompts using a **local design system** (catalog + tokens) and the **Claude API**. No MCP server required for the dashboard or chatbot.
- **Two applications:**
  1. **Dashboard** (port 3850) — Original single-page app: catalog browser, simple chat, generate + variants
  2. **Chatbot** (port 3851) — **PRIMARY** — ChatGPT-style agent with:
     - **Streaming chat** with full conversation memory (SSE)
     - **Inline live UI previews** in chat messages (iframe)
     - **Expandable fullscreen preview modal** with Desktop/Tablet/Mobile viewport switcher
     - **Multi-variant side-by-side previews** (2-3 variants in a grid, each expandable individually or all together)
     - **Quick Actions panel** — one-click shortcut buttons (Style: Minimal/Bold/Playful/Elegant/Corporate, Modify: Dark Mode/Responsive/Animation/Simplify, Enhance: Loading States/Error Handling/Hover Effects/etc.) — all go through chat with full conversation context
     - **Variants panel** — pick count (2/3) + style keywords → generates in chat with side-by-side preview
     - **Catalog panel** — browse design system components, click to generate in chat
     - **Code Files panel** — auto-saved with component names, viewable and copyable
     - **Resizable panels** — draggable resize handle between chat and right panel (260px–700px)
     - **Conversation history** — persisted in localStorage, organized by Today/Yesterday/Older

---

## 2. Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Python 3, `http.server` + `ThreadingMixIn` | Multi-threaded for concurrent requests |
| Frontend | React 18 (UMD from CDN), Babel standalone | No build step |
| Markdown | marked.js + highlight.js | GitHub Dark theme syntax highlighting |
| AI | Anthropic Claude API (`claude-sonnet-4-20250514`) | Streaming SSE for chat |
| Preview | iframe: React + Babel + Tailwind (CDN) | Sandboxed rendering |
| Persistence | localStorage | Conversation history |
| API key | `ANTHROPIC_API_KEY` from `.env` | Loaded by python-dotenv |
| Design data | `design_system/catalog.json`, `tokens.json` | Injected into Claude system prompt |

---

## 3. How to Run

### Chatbot (primary — recommended)
```
cd milestone1-agent/chatbot
python server.py
→ Open http://127.0.0.1:3851
```

### Dashboard (original)
```
cd milestone1-agent/dashboard
python server.py
→ Open http://127.0.0.1:3850
```

### Environment
- Create `.env` in project root with: `ANTHROPIC_API_KEY=your_key_here`
- Install deps: `pip install -r requirements.txt` (anthropic, python-dotenv)

---

## 4. Directory Structure

```
milestone1-agent/
├── .env                         # ANTHROPIC_API_KEY (gitignored)
├── .env.example                 # Template
├── PROJECT_CONTEXT.md           # THIS FILE — full context for agents
├── README.md                    # User-facing docs with flow diagrams
├── requirements.txt             # Python: anthropic, python-dotenv
│
├── chatbot/                     # ★ PRIMARY — ChatGPT-style Agent
│   ├── server.py                #   Threaded HTTP server, port 3851
│   ├── index.html               #   Shell: React/Babel/marked/hljs CDN
│   ├── app.jsx                  #   Full React app (~890 lines, no build step)
│   └── styles.css               #   Dark theme, all layout/components (~760 lines)
│
├── dashboard/                   # Original dashboard app
│   ├── server.py                #   HTTP server, port 3850
│   ├── index.html               #   Shell with catalog injection
│   ├── app.jsx                  #   React app with panels
│   └── styles.css               #   Dashboard styles
│
├── design_system/               # Shared design data (used by both apps)
│   ├── catalog.json             #   Component list (name, import, description)
│   └── tokens.json              #   Colors, typography, spacing tokens
│
├── docs/                        # Documentation assets
│   ├── pipeline-flow-diagram.png   # High-level technical pipeline diagram
│   └── user-flow-diagram.png       # Manager-friendly user flow diagram
│
├── scripts/                     # Utility scripts
│   ├── clone-component-library.ps1
│   └── clone-component-library.sh
│
├── docker-compose.yml           # Optional: MCP server in Docker
├── Dockerfile                   # Optional: MCP server container
├── server.py                    # Optional: MCP server (root level)
└── src/mcp-client.ts            # Optional: MCP client
```

---

## 5. Chatbot Backend (chatbot/server.py)

- **Port:** 3851
- **Threading:** `ThreadingMixIn` enables concurrent requests (chat streaming + preview fetches in parallel)
- **System prompt:** Built dynamically from `PROJECT_CONTEXT.md` + `design_system/catalog.json` + `design_system/tokens.json`
- **Model:** `claude-sonnet-4-20250514`
- **Max tokens:** 3000 for chat streaming

### Routes

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| GET | `/api/health` | — | `{ ok, has_api_key }` |
| GET | `/api/catalog` | — | `{ tokens, catalog }` |
| POST | `/api/chat/stream` | `{ message, history }` | SSE stream: `{"type":"chunk","text":"..."}` then `{"type":"done"}` |
| POST | `/api/chat` | `{ message, history }` | `{ content }` |
| POST | `/api/preview` | `{ code }` | Full HTML document for iframe rendering |
| POST | `/api/generate` | `{ prompt }` | `{ code }` |
| POST | `/api/generate-variants` | `{ prompt, count, keywords }` | `{ variants: [{ code, keywords }] }` |

### Preview template
- Injects code into HTML with React 18 + ReactDOM + Babel + Tailwind CSS (all CDN)
- Auto-detects component name and appends `root.render(React.createElement(Name))` if missing
- Escapes `\` and `</script>` in user code

### System prompt rules
- Concise responses (1-3 sentences max text)
- Always output runnable code ending with `root.render(...)`
- Compact components (under 80 lines)
- Variant rules: separate jsx blocks, different component names, labeled headings

---

## 6. Chatbot Frontend (chatbot/app.jsx)

### Key Components

| Component | Purpose |
|-----------|---------|
| `App` | Main state: conversations, streaming, codeFiles, rightPanelWidth, resize logic |
| `Sidebar` | Conversation list grouped by date, new chat, delete |
| `WelcomeScreen` | Suggestion cards when no conversation active |
| `MarkdownContent` | Renders markdown with highlight.js code blocks + copy buttons |
| `PreviewModal` | Fullscreen modal — single (with viewport switcher) or multi-variant (side-by-side) |
| `InlinePreview` | Fetches `/api/preview`, renders iframe, expand button, code section, retry |
| `MultiPreview` | Side-by-side variant grid with per-variant expand + "Expand All" button |
| `Message` | Renders user/assistant messages; detects single vs multi code blocks |
| `InputArea` | Auto-growing textarea, send/stop buttons |
| `CodePanel` | Right panel top: list of saved code files with names, viewer, copy |
| `FeaturesPanel` | Right panel bottom: Quick Actions / Variants / Catalog tabs — all through chat |

### Code Extraction Functions

| Function | Purpose |
|----------|---------|
| `extractBestRunnableCodeBlock(text)` | Finds the best single runnable code block |
| `extractAllRunnableCodeBlocks(text)` | Finds ALL runnable blocks (for variant detection) |
| `extractVariantLabels(text)` | Extracts "## Variant N: Label" headings |
| `extractComponentName(code)` | Finds component name for file naming |
| `textWithoutAnyCodeBlocks(text)` | Strips all code blocks → clean prose for bubble text |

### Message Processing Flow
1. Claude streams full response → accumulated in `streamingContent`
2. On done: `processAssistantMessage(fullContent)` runs
3. Extracts all runnable blocks → if 2+, stores as `codes[]` + `variantLabels[]`
4. If single block: stores as `code`
5. Strips code from bubble text → `bubbleText` (clean prose)
6. Saves each code to `codeFiles` with smart names (component name or variant label)
7. Message stored: `{ role, content, bubbleText, code, codes, variantLabels }`
8. Rendering: single code → `InlinePreview`, multiple codes → `MultiPreview`

### Features Panel (Shortcut Tool)
- **Quick Actions tab:** Pre-built prompts sent to chat. Categories: Style, Modify, Enhance. Each appends "Output complete React component..." rule to ensure preview works.
- **Variants tab:** Pick count + keywords → builds prompt → sends to chat. Also has quick preset buttons (Light vs Dark, Compact vs Spacious, Min/Bold/Fun).
- **Catalog tab:** Clickable components → sends generation prompt to chat.
- All features use `onSendToChat(msg)` which calls the same `sendMessage` as typing — full conversation memory.

### Resize Handle
- `startResize` callback on `onMouseDown`
- Tracks mouse movement → updates `rightPanelWidth` state (260px–700px)
- Applied as inline style on right panel

---

## 7. Chatbot Styles (chatbot/styles.css)

- **Theme:** Dark (--bg: #0d0d0d, --bg-chat: #212121, --accent: #6366f1 indigo)
- **Layout:** Three-column flex: sidebar (260px) | chat (flex:1) | right panel (380px default, resizable)
- **Key sections:** sidebar, chat header, messages, inline preview, fullscreen modal, multi-preview grid, code blocks (max-height 280px scrollable), input area, right panel (code files + features), shortcut buttons (pill-shaped), responsive (mobile: right panel hidden, sidebar overlay)

---

## 8. Dashboard Backend & Frontend (dashboard/)

- **Port:** 3850
- Same structure as chatbot but simpler: no streaming, no multi-variant detection, no quick actions
- Has CatalogPanel, ChatPanel, GeneratePanel, AgentPanel
- Serves as the original app; chatbot is the enhanced version

---

## 9. Design System

- **`design_system/catalog.json`** — Component array: `{ name, import/path, description }`
- **`design_system/tokens.json`** — Colors, typography, spacing
- Both loaded into Claude's system prompt so generated code follows design system
- Catalog browsable in the Chatbot's Catalog tab (right panel)

---

## 10. Conventions and Important Behavior

- **All features go through chat** — Quick Actions, Variants, Catalog clicks all send prompts to chat. No separate generation UI. Full conversation memory.
- **Code extraction:** All fenced code blocks stripped from bubble text. Best/all runnable blocks used for previews.
- **Preview sandbox:** Code runs in an iframe with React + Babel + Tailwind from CDN. Server auto-appends `root.render(...)` if missing.
- **Multi-variant detection:** If response has 2+ runnable code blocks → shown side-by-side with individual + combined expand.
- **File naming:** Code files named by extracted component name (e.g. "DashboardCard") or variant label (e.g. "CardMinimal — Minimal").
- **Concise output:** System prompt enforces brief text (1-3 sentences) and compact code (under 80 lines).
- **localStorage:** Conversations persisted client-side. No server-side storage.

---

## 11. For a New Cursor Agent: What to Do

1. **Read this file** to understand the full project
2. **Run the chatbot:** `cd chatbot && python server.py` → open http://127.0.0.1:3851
3. **Env:** Ensure `.env` with `ANTHROPIC_API_KEY` exists at project root
4. **Chatbot UI changes:** Edit `chatbot/app.jsx` (React) and `chatbot/styles.css`
5. **Chatbot API changes:** Edit `chatbot/server.py`; routes in `do_GET` / `do_POST`
6. **Dashboard changes:** Same pattern in `dashboard/` folder
7. **Design data:** Edit `design_system/catalog.json` and `tokens.json`
8. **README:** Update `README.md` and diagrams in `docs/` if pipeline changes

---

## 12. One-Line Summary

**ChatGPT-style design system agent (React + Python + Claude) with streaming chat, inline live UI previews, expandable fullscreen modal with viewport switcher, side-by-side variant generation, one-click quick action shortcuts, draggable resizable panels, auto-named code file saving, and design system catalog integration — all running through a single conversation with full memory.**
