# Full Project Context — Milestone 1 Design System Agent

**Use this file when starting a new Cursor chat or handing off to another agent.** It describes the full project state, architecture, how to run it, and all important decisions so work can continue seamlessly.

---

## 1. What This Project Is

- **Name:** Milestone 1 — Design System Agent
- **Purpose:** Multi-agent system that generates production-quality React/JSX UI components from natural language prompts, using the Untitled UI design system.
- **Architecture:** 4-agent LangGraph pipeline (Orchestrator → Discovery → Generator → QA) with 6 tools + RAG
- **LLM:** Claude Sonnet (code generation via Anthropic) + GPT-4o-mini (classification, discovery, chat via OpenAI) + OpenAI Embeddings (RAG only)
- **Frontend:** ChatGPT-style chatbot with real-time agent pipeline visualization + collapsible thinking bar

---

## 2. Multi-Agent System (LangGraph)

### 4 Agents (OPTIMIZED — minimal LLM calls)

| Agent | File | Model | Role | Speed |
|-------|------|-------|------|-------|
| **Orchestrator** | `agent/orchestrator.py` | GPT-4o-mini (skipped if pre-classified) | Classifies request → routes to sub-agents → manages QA retry loop | ~0-1s |
| **Discovery** | `agent/discovery.py` | GPT-4o-mini | Single LLM call with pre-loaded catalog, returns Tailwind patterns | ~1-2s |
| **Generator** | `agent/generator.py` | Claude Sonnet (Anthropic) | Single LLM call, writes complete React/JSX code with Untitled UI patterns | ~10-15s |
| **QA Reviewer** | `agent/reviewer.py` + inline | Rule-based (no LLM) | Calls verify_quality + check_accessibility directly | ~0.1s |

**Key optimizations:**
- Pre-classification in `chatbot/server.py` does full intent classification (generate/discover/review/chat) in one GPT-4o-mini call, then passes the result to the pipeline so `classify_node` **skips its LLM call entirely**.
- Discovery is a single GPT-4o-mini call with pre-loaded catalog. QA is pure regex — zero LLM calls.
- Generator prompt includes **exact Untitled UI Tailwind patterns** for buttons, cards, tables, badges, avatars, inputs, tabs, modals, toggles, typography, and layout.

### 6 Tools

| Tool | File | Type | Purpose |
|------|------|------|---------|
| `list_components` | `agent/tools.py` | MCP-equivalent | Lists all 24 components from catalog.json |
| `get_component_spec` | `agent/tools.py` | MCP-equivalent | Gets full spec + Tailwind patterns for one component |
| `get_design_tokens` | `agent/tools.py` | MCP-equivalent | Gets colors, typography, spacing, shadows from tokens.json |
| `preview_component` | `agent/tools.py` | Custom | Saves code as preview.html (React+Babel+Tailwind sandbox) |
| `verify_quality` | `agent/tools.py` | Custom | Rule-based: PascalCase, Tailwind, no imports, Untitled UI compliance |
| `check_accessibility` | `agent/tools.py` | Custom | Rule-based: semantic HTML, aria-labels, focus states, contrast |

### RAG System

| Component | File | Details |
|-----------|------|---------|
| **RAG Module** | `agent/rag.py` | In-memory vector store with OpenAI text-embedding-3-small |
| **Index** | 56 chunks | 24 components + 6 token categories + ~26 doc sections |
| **Cache** | `design_system/.rag_cache/` | .npy embeddings cached to disk, auto-rebuilds on file changes |
| **Injection** | 2 points | `chatbot/server.py` (_handle_direct_chat) + `agent/orchestrator.py` (respond_node chat path) |

### Pipeline Flows

```
"generate" request:  Pre-classify(GPT-4o-mini) → [Pipeline: Classify(skip) → Discovery(GPT-4o-mini) → Generation(Claude Sonnet) → QA(rule-based) → Respond]
"discover" request:  Pre-classify(GPT-4o-mini) → [Pipeline: Classify(skip) → Discovery(GPT-4o-mini) → Respond]
"review" request:    Pre-classify(GPT-4o-mini) → [Pipeline: Classify(skip) → QA(rule-based) → Respond]
"chat" request:      Pre-classify(GPT-4o-mini) → Direct GPT-4o-mini + RAG (no pipeline)
```

### Smart Routing (Pre-Classification) — OPTIMIZED

`chatbot/server.py` runs `_fast_classify()` using GPT-4o-mini which does **full classification** in one call:
- Returns `"generate"`, `"discover"`, `"review"`, or `"chat"` (not just "pipeline"/"chat")
- **"chat"** → Direct GPT-4o-mini response with RAG context (fast, cheap, no pipeline)
- **"generate"/"discover"/"review"** → Passed as `workflow` param to pipeline, so `classify_node` **skips its LLM call**

This eliminates a redundant ~1-2s LLM call that the old system made.

### State Shape (OrchestratorState)

```python
{
    "messages": [...],          # LangChain message history
    "workflow": "generate",     # Pre-classified by chatbot/server.py OR set by classify_node
    "user_request": "...",      # exact user message (stored by classify node)
    "discovery_output": "...",  # components + Tailwind patterns
    "generated_code": "...",    # React/JSX code from generator
    "qa_result": "...",         # PASS/FAIL verdict from QA
    "retry_count": 0,           # QA retry counter (max 2)
}
```

### SSE Event Types (agent/server.py → frontend)

```json
{"type": "status", "text": "Analyzing your request..."}
{"type": "status", "text": "Searching component library..."}
{"type": "status", "text": "Generating React code..."}
{"type": "status", "text": "Reviewing code quality..."}
{"type": "status", "text": "Preparing response..."}
{"type": "thinking", "text": "discovery/generation tokens..."}
{"type": "chunk", "text": "final response content..."}
{"type": "done"}
{"type": "error", "error": "message"}
```

**Key distinction:** `thinking` events carry discovery/generation LLM tokens (hidden in collapsible bar). `chunk` events carry only the final formatted response (shown in chat). This keeps the chat clean.

Pipeline timing is logged to server console: `[pipeline] <node> started/finished at Xs`

---

## 3. Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Code Generation LLM | **Claude Sonnet (Anthropic)** | `claude-sonnet-4-20250514` — used in generator + generate_code + generate_variants |
| Classification/Chat/Discovery LLM | **OpenAI GPT-4o-mini** | Fast, cheap — classify, discovery, direct chat, respond chat path |
| Embeddings | **OpenAI text-embedding-3-small** | RAG vector embeddings for design system knowledge |
| RAG Store | **numpy** (in-memory + disk cache) | Cosine similarity search, ~56 chunks, <100ms queries |
| Agent Framework | **LangGraph** + LangChain | StateGraph orchestrator + direct LLM calls (no ReAct loops) |
| Backend | Python 3, `http.server` + `ThreadingMixIn` | Threaded for concurrent requests |
| Frontend | React 18 (UMD CDN), Babel standalone | No build step |
| Markdown | marked.js + highlight.js | GitHub Dark syntax highlighting |
| Preview | iframe: React + Babel + Tailwind (CDN) | Sandboxed rendering with Untitled UI Tailwind config |
| Persistence | localStorage | Conversations (client-side only) |
| API Keys | `OPENAI_API_KEY` + `ANTHROPIC_API_KEY` from `.env` | Loaded by python-dotenv |
| Design Data | `design_system/catalog.json` + `tokens.json` | Read by tools, RAG, and discovery |
| Environment | `USE_LANGGRAPH=true` in `.env` | Toggles multi-agent vs direct streaming mode |

---

## 4. How to Run

```bash
cd milestone1-agent
pip install -r requirements.txt       # openai, anthropic, langgraph, langchain-*, numpy, etc.
cd chatbot
python server.py                       # → http://localhost:3851
```

### Environment (.env in project root)

```
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
USE_LANGGRAPH=true
```

- `OPENAI_API_KEY` — **Required.** Used for: embeddings (RAG), classification (GPT-4o-mini), discovery (GPT-4o-mini), chat responses
- `ANTHROPIC_API_KEY` — **Required for code generation.** Used for: Claude Sonnet in generator, generate_code(), generate_variants(). Falls back to GPT-4o if missing
- `USE_LANGGRAPH=true` → routes through the 4-agent LangGraph pipeline
- `USE_LANGGRAPH=false` or unset → direct Claude/GPT streaming (fallback)

### Windows: Kill old processes before restart

```powershell
netstat -ano | Select-String ":3851"
taskkill /F /PID <pid>
```

---

## 5. Directory Structure

```
milestone1-agent/
├── .env                              # API keys + USE_LANGGRAPH (gitignored)
├── .env.example                      # Template
├── PROJECT_CONTEXT.md                # ★ THIS FILE — full context for new sessions
├── coding_guidelines.md              # Injected into Generator prompt
├── requirements.txt                  # openai, anthropic, langgraph, langchain-*, numpy
│
├── agent/                            # ★ Multi-Agent System (LangGraph)
│   ├── __init__.py                   #   Package docstring
│   ├── orchestrator.py               #   Agent 1: Supervisor StateGraph (classify → route → retry)
│   ├── discovery.py                  #   Agent 2: Fast discovery (GPT-4o-mini, single call, pre-loaded catalog)
│   ├── generator.py                  #   Agent 3: Code Generation (Claude Sonnet, enhanced Untitled UI prompt)
│   ├── reviewer.py                   #   Agent 4: QA Review prompt (used by rule-based QA node)
│   ├── tools.py                      #   All 6 tools (3 MCP-equiv + 3 custom + Untitled UI compliance)
│   ├── rag.py                        #   ★ RAG: vector index over catalog/tokens/docs, query function
│   ├── server.py                     #   Async SSE streaming with thinking/chunk event separation
│   └── mcp_client.py                 #   FastMCP client (reference for M2, not used in M1)
│
├── chatbot/                          # ★ PRIMARY Frontend — ChatGPT-style Agent UI
│   ├── server.py                     #   HTTP server (port 3851), smart routing, Claude for gen, GPT for chat
│   ├── index.html                    #   Shell: React/Babel/marked/hljs CDN
│   ├── app.jsx                       #   Full React app (~1100 lines) with ThinkingBar + AgentPipeline
│   ├── styles.css                    #   Dark theme + thinking bar + pipeline visualization CSS
│   └── preview.html                  #   Auto-generated by preview_component tool
│
├── dashboard/                        # Original dashboard app (port 3850, secondary)
│   ├── server.py
│   ├── index.html
│   ├── app.jsx
│   └── styles.css
│
├── design_system/                    # ★ Shared design data (read by agent tools + RAG)
│   ├── catalog.json                  #   24 components with Tailwind recreation patterns
│   ├── tokens.json                   #   Full Untitled UI palette, typography, shadows
│   └── .rag_cache/                   #   Cached embeddings (gitignored)
│
├── docs/                             # Documentation + diagrams
│   ├── architecture.md
│   ├── database-plan.md
│   ├── message-schemas.md
│   ├── discovery-agent-architecture.excalidraw  # ★ NEW: Discovery agent diagram
│   ├── deliverable-overview.excalidraw
│   ├── plan.excalidraw.png
│   └── pipeline-flow-diagram.png
│
└── scripts/
    ├── clone-component-library.ps1
    └── clone-component-library.sh
```

---

## 6. Chatbot Backend (chatbot/server.py)

- **Port:** 3851
- **Code Generation:** Claude Sonnet via Anthropic SDK (`_get_anthropic_client()`)
- **Classification/Chat:** GPT-4o-mini via OpenAI SDK (`_get_openai_client()`)
- **Threading:** `ThreadingMixIn` for concurrent requests
- **Env loading:** `_load_env()` reads ALL vars from `.env` via python-dotenv
- **Smart Routing:** `_fast_classify()` does **full classification** (generate/discover/review/chat) and passes workflow to pipeline

### Routes

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| GET | `/api/health` | — | `{ ok, has_api_key }` |
| GET | `/api/catalog` | — | `{ tokens, catalog }` |
| POST | `/api/chat/stream` | `{ message, history }` | SSE stream (status + thinking + chunk + done) |
| POST | `/api/chat` | `{ message, history }` | `{ content }` (non-streaming, GPT-4o) |
| POST | `/api/preview` | `{ code }` | Full HTML for iframe (with Untitled UI Tailwind config) |
| POST | `/api/generate` | `{ prompt }` | `{ code }` (Claude Sonnet) |
| POST | `/api/generate-variants` | `{ prompt, count, keywords }` | `{ variants }` (Claude Sonnet) |

### Streaming flow when `USE_LANGGRAPH=true`

1. `handle_stream()` → `_fast_classify(message)` → returns "generate"/"discover"/"review"/"chat"
2. If `"chat"` → `_handle_direct_chat()` (GPT-4o-mini streaming + RAG context, fast)
3. If `"generate"/"discover"/"review"` → `_handle_langgraph_stream(message, history, workflow=...)` → `agent.server.run_agent_stream()`
4. SSE events: status → thinking (discovery/gen tokens, hidden in bar) → chunk (final response) → done

### Helper Functions

- `_get_anthropic_client()` — Returns `anthropic.Anthropic` client for Claude API
- `_get_openai_client()` — Returns `openai.OpenAI` client (used for RAG embeddings + chat)
- `_prepare_anthropic_messages()` — Converts OpenAI-style messages to Anthropic format (extracts system, merges consecutive same-role)
- `generate_code()` — Uses Claude Sonnet for single component generation
- `generate_variants()` — Uses Claude Sonnet for 2-3 variant generation

### Preview Template Features

- Untitled UI Tailwind config (custom colors, shadows, border-radius, Inter font)
- Console error capture via `window.onerror` → reports to parent via `postMessage`
- "Untitled UI" watermark badge in bottom-right corner
- Import statement stripping and duplicate root declaration removal

---

## 7. Chatbot Frontend (chatbot/app.jsx)

### Key Components

| Component | Purpose |
|-----------|---------|
| `App` | Main state: conversations, streaming, agentStep, pipelineVisible, codeFiles, thinkingContent |
| `ThinkingBar` | ★ NEW: Collapsible thinking bar (like Cursor) — shows discovery/generation output hidden by default |
| `AgentPipeline` | Real-time pipeline visualization (5 nodes: Classify→Discovery→Generate→QA→Respond) |
| `Sidebar` | Conversation history grouped by date |
| `WelcomeScreen` | Suggestion cards with multi-agent description |
| `MarkdownContent` | Renders markdown + highlight.js code blocks |
| `PreviewModal` | Fullscreen preview — single (with viewport switcher) or multi-variant |
| `InlinePreview` | Inline iframe preview + expand + code toggle |
| `MultiPreview` | Side-by-side variant grid |
| `Message` | User/assistant messages with ThinkingBar + auto-detected previews |
| `InputArea` | Auto-growing textarea with send/stop |
| `CodePanel` | Right panel: saved code files |
| `FeaturesPanel` | Right panel: Quick Actions / Variants / Catalog tabs |

### ThinkingBar (NEW — Cursor-style collapsible thinking)

- During generation: shows a pulsing "Thinking..." bar with the discovery/generation output hidden inside
- After completion: collapses to "Thought for X lines" — click to expand and see full thinking
- Thinking content is saved with each message (`thinkingContent` field) so it persists across conversations
- Backend sends `{"type": "thinking"}` events for discovery/generation tokens (not shown in chat)
- Backend sends `{"type": "chunk"}` events only for the final formatted response (shown in chat)

### Chat State Management

- **`conversationsRef`**: A ref that always holds the latest conversations state, used by `sendMessage` to avoid stale closures
- **`thinkingContent`**: State variable that accumulates thinking tokens during streaming
- **History truncation**: Assistant messages in history have code blocks replaced with `[code block omitted]` and truncated to 500 chars to save tokens
- **History sent to backend**: Last 20 messages with `{role, content}` format

### Code Extraction

- `extractBestRunnableCodeBlock()`: Scoring system prioritizes blocks with `root.render` (+50000) and PascalCase components (+30000)
- `extractAllRunnableCodeBlocks()`: For variant detection (multiple complete components)
- Streaming: Detects unclosed code fences and strips them to avoid rendering raw code

---

## 8. Design System Data

### catalog.json (24 components)

Each component includes:
- `name`, `description`, `props`
- **`tailwind_pattern`** — exact Tailwind CSS recreation pattern for browser sandbox
- **`variants`** — different style options with Tailwind classes

**Components:** Button, Input, Badge, Avatar, Card, Table, Tabs, Modal, Select, Checkbox, EmptyState, StatsCard, SearchInput, ProgressBar, Toggle, Radio, Textarea, Dropdown, Tooltip, Tag, Pagination, FileUpload, LoadingIndicator, Notification

Also includes `layout_patterns` (page, container, card grid, sidebar) and `icon_patterns` (inline SVGs)

### tokens.json (Untitled UI palette)

- **9 color families:** primary/blue, gray, success/emerald, error/red, warning/amber, purple, indigo, rose (full shade ranges 25-900)
- **Typography:** Inter font, 8 sizes (xs-4xl), 4 weights, 3 line heights
- **Spacing:** 16 values (0.5-24)
- **Border radius:** 7 values (none-full)
- **Shadows:** 5 levels (xs-xl) with Untitled UI shadow values
- **tailwindMapping:** primary→blue, success→emerald, error→red, warning→amber

### coding_guidelines.md

Injected into Generator's prompt. Covers:
- PascalCase naming, function components only
- Tailwind CSS only (no inline styles)
- Accessibility: focus states, semantic HTML, aria-labels
- No imports (React/ReactDOM global via CDN)
- Component structure pattern
- Variant generation rules

---

## 9. Generator Prompt (ENHANCED)

The generator in `agent/generator.py` has an extensively detailed system prompt that includes:

### Exact Untitled UI Tailwind Patterns (baked into prompt)

- **Buttons**: Primary (`bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm`), Secondary, Destructive, Ghost
- **Inputs**: Field with label, search input with icon
- **Cards**: Container (`bg-white border-gray-200 rounded-xl shadow-sm`), header/body sections, stats card
- **Tables**: Wrapper with rounded-xl, thead bg-gray-50, tbody divide-y, hover rows
- **Badges**: Success (emerald), Error (red), Warning (amber), Info (blue), Default (gray)
- **Avatars**: Small/Medium with initials, image variant
- **Layout**: Page (min-h-screen bg-gray-50), container, section headers
- **Typography**: Page title, section title, body, caption, link
- **Tabs**: Container with border-b, active/inactive states
- **Modal**: Overlay with backdrop-blur, panel with rounded-xl, header/footer
- **Toggle**: Track ON/OFF with thumb transition
- **Icons**: Inline SVG conventions (20x20, stroke-based)

This ensures generated code matches the Untitled UI design system exactly, not generic Tailwind.

---

## 10. QA System Details

The QA system runs two rule-based tools **directly** (no LLM agent — instant execution):

**verify_quality** (scoring from 100):
- PascalCase component name (-15 if missing)
- className/Tailwind usage (-10 if absent)
- No inline styles (-5)
- root.render present (-15 if missing)
- Under 150 lines (-5 if over)
- No import statements (-10)
- No hardcoded hex colors (-5)
- No class components (-15)
- **Untitled UI compliance:**
  - Button/Input must use rounded-lg (-5)
  - Cards must use rounded-xl (-5)
  - Non-standard colors flagged: teal, cyan, lime, fuchsia, etc. (-5)
  - Font-family override check (-5)
  - Table tbody must use divide-y divide-gray-200 (-5)

**check_accessibility** (scoring from 100):
- Semantic HTML tags (-10 if missing)
- aria-label on icon buttons (-15 if missing)
- alt on images (-15 if missing)
- Labels on form inputs (-15 if missing)
- Focus state classes (-10 if missing)
- Color contrast check (-5 for very light text)

Verdict: PASS if score >= 70 and no errors. FAIL triggers retry (max 2 attempts).

---

## 11. RAG System Details

**File:** `agent/rag.py`

### How It Works
1. **Indexing** (`build_index()`): Chunks catalog.json (24 component chunks), tokens.json (6 category chunks), PROJECT_CONTEXT.md (~8 section chunks), coding_guidelines.md (~4 section chunks) = ~56 total chunks
2. **Embedding**: OpenAI `text-embedding-3-small` embeds all chunks into float32 vectors
3. **Caching**: Embeddings saved as `.npy` files in `design_system/.rag_cache/` with fingerprint-based invalidation
4. **Querying** (`query(text, k=3)`): Embeds the query, cosine similarity against all chunks, returns top-k

### Injection Points
- **`chatbot/server.py` → `_handle_direct_chat()`**: RAG context injected as system message after main prompt
- **`agent/orchestrator.py` → `respond_node()` chat path**: RAG context injected before conversation history

---

## 12. Important Decisions & Gotchas

- **Claude Sonnet for code generation:** Generator uses `ChatAnthropic(model="claude-sonnet-4-20250514")`. Chatbot server's `generate_code()` and `generate_variants()` use the Anthropic SDK directly. Falls back to GPT-4o if `ANTHROPIC_API_KEY` is not set.
- **GPT-4o-mini for fast tasks:** Classification, discovery, and chat use GPT-4o-mini. Claude Haiku was attempted but returned 404 errors with the available API key, so GPT-4o-mini is used instead.
- **Pre-classification eliminates redundant LLM call:** `_fast_classify()` in `chatbot/server.py` does full classification and passes the result as `workflow` to `run_agent_stream()`. The `classify_node` in the pipeline checks if workflow is already set and skips its LLM call.
- **Thinking vs Chunk events:** `agent/server.py` tracks the current node. LLM tokens from `discovery`/`generation` nodes are sent as `{"type": "thinking"}`. Only `respond` node tokens are sent as `{"type": "chunk"}`. This keeps the chat clean.
- **ThinkingBar component:** Frontend shows a collapsible bar (like Cursor's thinking indicator) for thinking events. Collapsed by default, expandable to see full discovery/generation output.
- **No ReAct loops in Discovery/QA:** Discovery is a single GPT-4o-mini call with pre-loaded catalog. QA calls regex tools directly. This eliminates ~15 unnecessary LLM round-trips.
- **Chat state uses ref:** `conversationsRef` in app.jsx ensures `sendMessage` always has the latest conversation state, fixing the stale closure bug.
- **History truncation:** Assistant messages in history have code blocks stripped and are truncated to 500 chars to avoid wasting tokens on repeated code.
- **RAG auto-rebuilds:** The RAG index checks source file mtimes and rebuilds automatically when catalog.json, tokens.json, or docs change.
- **Preview templates:** Both `chatbot/server.py` and `agent/tools.py` have matching preview HTML templates with full Untitled UI Tailwind config (custom colors, Inter font, shadows, border-radius).
- **`_load_env()` loads ALL vars:** The chatbot server's env loader reads every `KEY=VALUE` from `.env`. Critical for `USE_LANGGRAPH`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY`.
- **Multiple processes on port 3851:** On Windows, always kill old processes before restarting: `netstat -ano | Select-String ":3851"` then `taskkill /F /PID <pid>`
- **Anthropic helper functions:** `chatbot/server.py` has `_get_anthropic_client()` and `_prepare_anthropic_messages()` for Claude API calls. The prepare function extracts system messages and merges consecutive same-role messages (Anthropic requirement).

---

## 13. Recent Changes (This Session)

### What Changed
1. **Switched code generation to Claude Sonnet** — `generate_code()`, `generate_variants()`, and the pipeline generator all use `claude-sonnet-4-20250514` via Anthropic SDK
2. **Pre-classification optimization** — `_fast_classify()` now returns full intent (generate/discover/review/chat), pipeline `classify_node` skips LLM when workflow is pre-set
3. **Enhanced generator prompt** — Added exact Untitled UI Tailwind patterns (buttons, cards, tables, badges, avatars, modals, tabs, toggles, typography, layout) for pixel-perfect design fidelity
4. **Thinking bar (Cursor-style)** — New `ThinkingBar` component shows discovery/generation output as a collapsible bar, keeping the chat clean
5. **SSE thinking events** — `agent/server.py` now sends `{"type": "thinking"}` for discovery/generation tokens, `{"type": "chunk"}` only for final response
6. **Timing improvement** — Eliminated redundant classify LLM call (~2s saved). Total generate pipeline: ~12-18s (down from ~19-27s)
7. **New deliverable** — `docs/discovery-agent-architecture.excalidraw` showing Discovery Agent architecture and connections

### What Was Attempted But Reverted
- **Claude Haiku for classify/discovery/chat** — Attempted `claude-3-5-haiku-20241022` and `claude-haiku-4-5-20251001` but both returned 404 with the available API key. Reverted to GPT-4o-mini for all fast tasks.

---

## 14. Milestone Roadmap

| Milestone | Status | Description |
|-----------|--------|-------------|
| **M1: Local LangGraph** | ★ CURRENT | 4 agents, 6 local tools, RAG, Claude Sonnet + GPT-4o-mini, ChatGPT-style UI with thinking bar |
| **M2: Ctrlagent Maker** | PLANNED | Migrate agents to Ctrlagent Maker platform, MCP server tools, Keycloak auth |
| **M3: Production** | PLANNED | Pulse dashboards, PostgreSQL persistence, full deployment |

---

## 15. For a New Cursor Agent: Quick Start

1. **Read this file** to understand the full project
2. **Run:** `cd milestone1-agent/chatbot && python server.py` → open http://localhost:3851
3. **Env:** Ensure `.env` at project root has `OPENAI_API_KEY=...`, `ANTHROPIC_API_KEY=...`, and `USE_LANGGRAPH=true`
4. **Agent changes:** Edit files in `agent/` directory (orchestrator, discovery, generator, reviewer, tools, rag)
5. **Frontend changes:** Edit `chatbot/app.jsx` (React) and `chatbot/styles.css`
6. **Backend changes:** Edit `chatbot/server.py` for API routes
7. **Design system:** Edit `design_system/catalog.json` and `tokens.json` (RAG auto-rebuilds)
8. **Dependencies:** `pip install -r requirements.txt` (openai, anthropic, langgraph, langchain-openai, langchain-anthropic, numpy)
9. **Kill old processes:** On Windows, always check `netstat -ano | Select-String ":3851"` and kill before restart

---

## 16. One-Line Summary

**Multi-agent design system chatbot (4 LangGraph agents + 6 tools + RAG + Claude Sonnet for code gen + GPT-4o-mini for chat/classify/discovery) with 24-component Untitled UI catalog, enhanced generator prompt with exact Tailwind patterns, Cursor-style collapsible thinking bar, real-time pipeline visualization, inline live UI previews, Untitled UI compliance checks, and ChatGPT-style conversation UI.**
