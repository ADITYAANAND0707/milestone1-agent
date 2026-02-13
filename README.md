# Milestone 1 — Design System Agent

> An AI-powered UI generation system that uses a local design system catalog + Claude to generate, preview, and iterate on React components — all from natural language prompts.

---

## Visual Flow Diagrams

> These diagrams can be shared as screenshots with your team. Saved in `docs/` folder.

### High-Level Pipeline
![High-Level Pipeline](docs/pipeline-flow-diagram.png)

### User Flow (Manager-Friendly)
![User Flow](docs/user-flow-diagram.png)

---

## High-Level Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MILESTONE 1 — DESIGN SYSTEM AGENT                   │
│                                                                             │
│   ┌──────────┐      ┌──────────────┐      ┌──────────────┐                │
│   │  USER     │─────▶│  CHATBOT UI  │─────▶│  PYTHON      │                │
│   │  (Prompt) │      │  (React SPA) │      │  SERVER      │                │
│   └──────────┘      └──────┬───────┘      └──────┬───────┘                │
│                            │                      │                        │
│                            │     ┌────────────────┘                        │
│                            │     │                                         │
│                            ▼     ▼                                         │
│                     ┌──────────────────┐                                   │
│                     │   CLAUDE API     │                                   │
│                     │   (Anthropic)    │                                   │
│                     └────────┬─────────┘                                   │
│                              │                                             │
│                              ▼                                             │
│                     ┌──────────────────┐                                   │
│                     │  GENERATED CODE  │                                   │
│                     │  (React + JSX)   │                                   │
│                     └────────┬─────────┘                                   │
│                              │                                             │
│                    ┌─────────┼─────────┐                                   │
│                    ▼         ▼         ▼                                    │
│              ┌──────────┐ ┌────────┐ ┌──────────┐                         │
│              │  INLINE  │ │ CODE   │ │ EXPAND   │                         │
│              │  PREVIEW │ │ FILES  │ │ FULLSCR  │                         │
│              │ (iframe) │ │ PANEL  │ │ MODAL    │                         │
│              └──────────┘ └────────┘ └──────────┘                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### How It Works (Simple Version)

1. **You type a prompt** — "Build a dashboard card", "Make it dark mode", etc.
2. **Claude generates code** — React components using your design system tokens and catalog
3. **Live preview appears** — Right in the chat, inside an iframe, rendered in real-time
4. **Iterate with shortcuts** — Use Quick Actions or Variants to restyle without retyping
5. **Code is saved** — Every generated component is stored in the Code Files panel with a proper name

---

## Two Applications

| Application | Port | Purpose |
|-------------|------|---------|
| **Dashboard** | `3850` | Original single-page app: catalog browser, simple chat, generate + variants |
| **Chatbot** | `3851` | ChatGPT-style agent: streaming chat, inline previews, Quick Actions, side-by-side variants, expandable fullscreen, resizable panels |

Both share the same design system data (`design_system/`) and `.env` API key.

---

## Quick Start

```powershell
# 1. Install dependencies
cd milestone1-agent
pip install -r requirements.txt

# 2. Set your API key
#    Create .env in the project root:
#    ANTHROPIC_API_KEY=sk-ant-...

# 3. Run the Chatbot (recommended)
cd chatbot
python server.py
# Open http://127.0.0.1:3851

# OR run the Dashboard
cd dashboard
python server.py
# Open http://127.0.0.1:3850
```

---

## Detailed Technical Pipeline

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BROWSER (Client)                                    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐     │
│  │                          app.jsx (React 18 UMD)                         │     │
│  │                                                                         │     │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │     │
│  │  │ Sidebar  │  │  Chat Area   │  │  Right Panel │  │  Fullscreen  │   │     │
│  │  │          │  │              │  │              │  │  Modal       │   │     │
│  │  │ • Convos │  │ • Messages   │  │ • Code Files │  │              │   │     │
│  │  │ • New    │  │ • Streaming  │  │ • Quick Act. │  │ • Viewport   │   │     │
│  │  │ • Delete │  │ • Previews   │  │ • Variants   │  │   switcher   │   │     │
│  │  │          │  │ • Input bar  │  │ • Catalog    │  │ • Multi-var  │   │     │
│  │  └──────────┘  └──────┬───────┘  └──────┬───────┘  └──────────────┘   │     │
│  │                       │                  │                              │     │
│  │         ┌─────────────┘   ┌──────────────┘                              │     │
│  │         │                 │                                              │     │
│  │         ▼                 ▼                                              │     │
│  │  ┌──────────────────────────────┐                                       │     │
│  │  │   API Calls (fetch)          │                                       │     │
│  │  │   • SSE stream for chat      │                                       │     │
│  │  │   • POST for preview/gen     │                                       │     │
│  │  └──────────────┬───────────────┘                                       │     │
│  └─────────────────┼───────────────────────────────────────────────────────┘     │
│                    │                                                              │
└────────────────────┼──────────────────────────────────────────────────────────────┘
                     │  HTTP
                     ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│                          PYTHON SERVER (server.py)                                  │
│                          Port 3851 • ThreadingMixIn                                 │
│                                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                            API Routes                                        │  │
│  │                                                                              │  │
│  │  GET  /api/health ─────────▶ { ok, has_api_key }                            │  │
│  │  GET  /api/catalog ────────▶ { tokens, catalog }  ◀── design_system/*.json  │  │
│  │                                                                              │  │
│  │  POST /api/chat/stream ────▶ SSE: chunks → done   ◀── Claude API (stream)  │  │
│  │  POST /api/chat ───────────▶ { content }           ◀── Claude API           │  │
│  │  POST /api/preview ────────▶ HTML (iframe doc)     ◀── PREVIEW_HTML_TPL     │  │
│  │  POST /api/generate ───────▶ { code }              ◀── Claude API           │  │
│  │  POST /api/generate-variants▶ { variants[] }       ◀── Claude API           │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                    │
│  ┌────────────────────────────┐     ┌────────────────────────────────────────┐    │
│  │  System Prompt Builder     │     │  Preview Template                      │    │
│  │                            │     │                                        │    │
│  │  PROJECT_CONTEXT.md ──┐    │     │  React 18 + ReactDOM + Babel +         │    │
│  │  catalog.json ────────┼──▶ │     │  Tailwind CSS (CDN) + user code       │    │
│  │  tokens.json ─────────┘    │     │  → Rendered in sandboxed iframe        │    │
│  └────────────────────────────┘     └────────────────────────────────────────┘    │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
                     │
                     │  HTTPS
                     ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│                          ANTHROPIC CLAUDE API                                      │
│                                                                                    │
│  Model: claude-sonnet-4-20250514                                                  │
│  • Streaming (SSE) for real-time chat                                              │
│  • Non-streaming for generate / variants                                           │
│  • System prompt includes: project context + design tokens + component catalog     │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### Request Flow for Each Feature

#### Chat Message (Streaming)

```
User types → InputArea.send()
  → POST /api/chat/stream { message, history }
  → Server builds messages[] with full conversation history (last 30)
  → Claude API streaming (SSE)
  → Each chunk sent as: data: {"type":"chunk","text":"..."}
  → Frontend accumulates chunks → live markdown rendering
  → On done: extractAllRunnableCodeBlocks(fullContent)
    → If 1 block: InlinePreview (single iframe)
    → If 2+ blocks: MultiPreview (side-by-side iframes)
    → Code saved to CodePanel with component name
  → bubbleText = content minus code blocks (clean prose)
```

#### Quick Action (Shortcut Button)

```
User clicks "Minimal" / "Add Dark Mode" / etc.
  → Builds a prompt: "Redesign the last UI component with..."
    + "Output complete React component, must end with root.render..."
  → Calls sendMessage(prompt) — same as typing in chat
  → Goes through the full chat stream pipeline above
  → Claude has full conversation memory — knows the "last component"
  → New preview replaces in chat, code saved to panel
```

#### Variant Generation

```
User sets count (2/3) + keywords → clicks "Generate Variants in Chat"
  → Builds prompt: "Generate 2 variants... Variant 1: minimal. Variant 2: bold..."
  → Sent as chat message (full conversation context)
  → Claude responds with ## Variant 1 + ```jsx block, ## Variant 2 + ```jsx block
  → extractAllRunnableCodeBlocks() finds 2+ blocks
  → extractVariantLabels() gets "Minimal", "Bold" etc.
  → MultiPreview renders side-by-side iframes
  → "Expand All" opens fullscreen modal with variants side-by-side
  → Each variant saved to CodePanel: "CardMinimal — Minimal"
```

#### Preview Rendering

```
Code string → POST /api/preview { code }
  → Server checks if code has root.render()
    → If not: regex finds component name, appends root.render(...)
  → Injects code into PREVIEW_HTML_TPL
    → HTML doc with React 18 + ReactDOM + Babel + Tailwind (all CDN)
  → Returns full HTML document
  → Frontend loads into <iframe srcDoc={html}>
  → Expandable to fullscreen modal with viewport switcher (Desktop/Tablet/Mobile)
```

---

## Project Structure

```
milestone1-agent/
├── .env                         # ANTHROPIC_API_KEY (gitignored)
├── .env.example                 # Template
├── PROJECT_CONTEXT.md           # Full context for AI agents
├── README.md                    # This file
├── requirements.txt             # Python: anthropic, python-dotenv
│
├── chatbot/                     # ★ ChatGPT-style Agent (primary)
│   ├── server.py                #   Threaded HTTP server, port 3851
│   ├── index.html               #   Shell: React/Babel/marked/hljs CDN
│   ├── app.jsx                  #   Full React app (no build step)
│   └── styles.css               #   Dark theme, all layout/components
│
├── dashboard/                   # Original dashboard app
│   ├── server.py                #   HTTP server, port 3850
│   ├── index.html               #   Shell with catalog injection
│   ├── app.jsx                  #   React app with panels
│   └── styles.css               #   Dashboard styles
│
├── design_system/               # Shared design data
│   ├── catalog.json             #   Component list (name, import, desc)
│   └── tokens.json              #   Colors, typography, spacing
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

## Chatbot UI Features

### Three-Column Layout

```
┌──────────┬────────────────────────────────┬──────────────────┐
│          │                                │                  │
│ SIDEBAR  │         CHAT AREA             │  RIGHT PANEL     │
│          │                                │                  │
│ • New    │  ┌─────────────────────────┐  │ ┌──────────────┐ │
│   Chat   │  │ Assistant message       │  │ │ Code Files   │ │
│          │  │ "Here's the component"  │  │ │              │ │
│ • Today  │  │                         │  │ │ • DashCard   │ │
│   └ Conv │  │ ┌─────────────────────┐ │  │ │ • LoginForm  │ │
│   └ Conv │  │ │ ██ LIVE PREVIEW ██  │ │  │ │ • V1-Min     │ │
│          │  │ │ [Expand] [Copy]     │ │  │ │ • V2-Bold    │ │
│ • Older  │  │ │                     │ │  │ └──────────────┘ │
│   └ Conv │  │ │   (rendered UI)     │ │  │                  │
│          │  │ │                     │ │  │ ┌──────────────┐ │
│          │  │ └─────────────────────┘ │  │ │ Quick Actions│ │
│          │  │ ▶ Code used...          │  │ │              │ │
│          │  └─────────────────────────┘  │ │ [Minimal]    │ │
│          │                                │ │ [Bold]       │ │
│          │  ┌─────────────────────────┐  │ │ [Dark Mode]  │ │
│          │  │ You: "make it dark"     │  │ │ [Responsive] │ │
│          │  └─────────────────────────┘  │ │ [Animation]  │ │
│          │                                │ │              │ │
│          │  ┌─────────────────────────┐  │ │ Variants tab │ │
│          │  │ ┌──────────┬──────────┐ │  │ │ Catalog tab  │ │
│          │  │ │Variant 1 │Variant 2 │ │  │ └──────────────┘ │
│          │  │ │ [⛶] [Cp] │ [⛶] [Cp]│ │  │                  │
│          │  │ │ preview  │ preview  │ │  │                  │
│          │  │ └──────────┴──────────┘ │  │                  │
│          │  │ [⛶ Expand All]          │  │                  │
│          │  └─────────────────────────┘  │                  │
│          │                                │                  │
│          │  ╔═════════════════════════╗  │                  │
│          │  ║ Ask about the project..  ║  │                  │
│          │  ║                    [Send] ║  │                  │
│          │  ╚═════════════════════════╝  │                  │
├──────────┤◄─── drag to resize ──────────►├──────────────────┤
│ Powered  │                                │                  │
│ by Claude│                                │                  │
└──────────┴────────────────────────────────┴──────────────────┘
```

### Feature Summary

| Feature | Description |
|---------|-------------|
| **Streaming Chat** | Real-time SSE streaming with typing indicator and stop button |
| **Inline Preview** | Live UI rendered in iframe, directly in chat message |
| **Expand Preview** | Fullscreen modal with Desktop/Tablet/Mobile viewport switcher |
| **Multi-Variant** | 2-3 variants shown side-by-side with individual and combined expand |
| **Quick Actions** | One-click buttons: Style (Minimal, Bold...), Modify (Dark Mode...), Enhance (Loading States...) |
| **Code Files** | Auto-saved with component names, viewable and copyable from right panel |
| **Resizable Panels** | Drag the border between chat and right panel to resize |
| **Conversation History** | Persisted in localStorage, organized by Today/Yesterday/Older |
| **Catalog Browser** | Click any design system component to generate it in chat |
| **Markdown Rendering** | Full markdown with syntax highlighting (highlight.js) and copy buttons |

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Backend** | Python 3 `http.server` + `ThreadingMixIn` | Multi-threaded for concurrent preview + chat |
| **Frontend** | React 18 (UMD from CDN) | No build step, Babel standalone transpiles JSX in browser |
| **Markdown** | marked.js + highlight.js | Syntax highlighting with GitHub Dark theme |
| **AI** | Anthropic Claude API (`claude-sonnet-4-20250514`) | Streaming SSE for chat, non-streaming for generation |
| **Preview** | iframe with React + Babel + Tailwind (CDN) | Sandboxed rendering of generated components |
| **Persistence** | localStorage | Conversation history saved client-side |
| **Design Data** | `catalog.json` + `tokens.json` | Injected into Claude's system prompt |
| **Env** | `python-dotenv` | Loads `ANTHROPIC_API_KEY` from `.env` |

---

## API Reference (Chatbot Server — Port 3851)

| Method | Endpoint | Body | Response | Purpose |
|--------|----------|------|----------|---------|
| `GET` | `/api/health` | — | `{ ok, has_api_key }` | Health check |
| `GET` | `/api/catalog` | — | `{ tokens, catalog }` | Design system data |
| `POST` | `/api/chat/stream` | `{ message, history }` | SSE stream | Chat with Claude (streaming) |
| `POST` | `/api/chat` | `{ message, history }` | `{ content }` | Chat with Claude (non-streaming) |
| `POST` | `/api/preview` | `{ code }` | HTML document | Render code in preview template |
| `POST` | `/api/generate` | `{ prompt }` | `{ code }` | Generate single component |
| `POST` | `/api/generate-variants` | `{ prompt, count, keywords }` | `{ variants[] }` | Generate 2-3 style variants |

---

## Environment Setup

```env
# .env (in project root)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

**Requirements:**
```
anthropic>=0.39.0
python-dotenv>=1.0.0
```

Install: `pip install -r requirements.txt`

---

## Optional: MCP Server + Docker

For terminal-based flow with Claude Code (not required for dashboard/chatbot):

```bash
# Docker
docker compose up --build
# Server at http://127.0.0.1:3845/mcp

# Register with Claude Code
claude mcp add --transport http design-system http://127.0.0.1:3845/mcp
```

MCP exposes: `list_components`, `get_design_tokens`, `get_component_spec`, `generate_ui` tools and `design-system://tokens`, `design-system://components` resources.

---

## Design System Data

- **`design_system/catalog.json`** — Component list: name, import path, description
- **`design_system/tokens.json`** — Colors, typography, spacing tokens

Both are loaded into Claude's system prompt so generated code follows your design system conventions.
