# Full Project Context — Milestone 1 Design System Agent

**Use this file when starting a new Cursor chat or handing off to another agent.** It describes the full project state, architecture, how to run it, and all important decisions so work can continue seamlessly.

---

## 1. What This Project Is

- **Name:** Milestone 1 — Design System Agent
- **Purpose:** Multi-agent system that generates production-quality React/JSX UI components from natural language prompts, using switchable design system libraries (Untitled UI, Metafore, or Both).
- **Architecture:** 4-agent LangGraph pipeline (Orchestrator → Discovery → Generator → QA) with 6 tools + RAG, all library-aware
- **LLM:** Claude Sonnet (code generation via Anthropic) + GPT-4o-mini (classification, discovery, chat via OpenAI) + OpenAI Embeddings (RAG only)
- **Frontend:** ChatGPT-style chatbot with real-time agent pipeline visualization, collapsible thinking bar with text summaries, code pinning system, library switcher, and dark violet-accent color palette

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

### 6 Tools (Library-Aware)

| Tool | File | Type | Purpose |
|------|------|------|---------|
| `list_components` | `agent/tools.py` | MCP-equivalent | Lists components from the active library's catalog JSON |
| `get_component_spec` | `agent/tools.py` | MCP-equivalent | Gets full spec + Tailwind patterns for one component |
| `get_design_tokens` | `agent/tools.py` | MCP-equivalent | Gets colors, typography, spacing, shadows from the active library's tokens JSON |
| `preview_component` | `agent/tools.py` | Custom | Saves code as preview.html (React+Babel+Tailwind sandbox) |
| `verify_quality` | `agent/tools.py` | Custom | Rule-based: PascalCase, Tailwind, no imports, design system compliance |
| `check_accessibility` | `agent/tools.py` | Custom | Rule-based: semantic HTML, aria-labels, focus states, contrast |

Tools use `set_active_library(library)` (called from `classify_node`) to load the correct JSON files per selected library. When `library="both"`, catalogs are merged.

### RAG System (Library-Aware)

| Component | File | Details |
|-----------|------|---------|
| **RAG Module** | `agent/rag.py` | In-memory vector store with OpenAI text-embedding-3-small, per-library indexes |
| **Index** | ~56-112 chunks | Components + token categories + doc sections (varies by library) |
| **Cache** | `design_system/.rag_cache/` | Per-library .npy embeddings cached to disk (`embeddings_{library}_{fp}.npy`) |
| **Injection** | 2 points | `chatbot/server.py` (_handle_direct_chat) + `agent/orchestrator.py` (respond_node chat path) |

RAG maintains separate vector stores per library (`_stores` dict). When `library="both"`, chunks from both Untitled UI and Metafore are indexed together.

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
    "library": "untitledui",    # active design system: "untitledui" | "metafore" | "both"
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
| Design Data | `design_system/catalog.json`, `tokens.json`, `metafore_catalog.json`, `metafore_tokens.json` | Library-aware loading by tools, RAG, discovery, and generator |
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
├── agent/                            # ★ Multi-Agent System (LangGraph) — all library-aware
│   ├── __init__.py                   #   Package docstring
│   ├── orchestrator.py               #   Agent 1: Supervisor StateGraph (classify → route → retry), library in state
│   ├── discovery.py                  #   Agent 2: Fast discovery (GPT-4o-mini, library-aware catalog loading)
│   ├── generator.py                  #   Agent 3: Code Generation (Claude Sonnet, library-specific Tailwind patterns)
│   ├── reviewer.py                   #   Agent 4: QA Review prompt (used by rule-based QA node)
│   ├── tools.py                      #   All 6 tools (library-aware JSON loading via set_active_library)
│   ├── rag.py                        #   ★ RAG: per-library vector index over catalog/tokens/docs
│   ├── server.py                     #   Async SSE streaming, library param in state
│   └── mcp_client.py                 #   FastMCP client (reference for M2, not used in M1)
│
├── chatbot/                          # ★ PRIMARY Frontend — ChatGPT-style Agent UI
│   ├── server.py                     #   HTTP server (port 3851), library-aware loading, smart routing
│   ├── index.html                    #   Shell: React/Babel/marked/hljs CDN
│   ├── app.jsx                       #   Full React app (~1300 lines): library switcher, pin system, ThinkingBar
│   ├── styles.css                    #   Dark violet-accent theme + library selector + pin UI
│   └── preview.html                  #   Auto-generated by preview_component tool
│
├── dashboard/                        # Original dashboard app (port 3850, secondary)
│   ├── server.py
│   ├── index.html
│   ├── app.jsx
│   └── styles.css
│
├── design_system/                    # ★ Shared design data — multi-library support
│   ├── catalog.json                  #   Untitled UI: 24 components with Tailwind patterns
│   ├── tokens.json                   #   Untitled UI: palette (blue primary), typography, shadows
│   ├── metafore_catalog.json         #   ★ Metafore: 31 components with Tailwind patterns (purple brand)
│   ├── metafore_tokens.json          #   ★ Metafore: palette (purple primary), typography, shadows
│   ├── metafore catlog/              #   Source TSX files for Metafore primitives
│   │   └── primitives_catalog/       #   30 TSX components, theme.css, spec.md, README.md
│   └── .rag_cache/                   #   Per-library cached embeddings (gitignored)
│
├── docs/                             # Documentation + diagrams
│   ├── architecture.md
│   ├── database-plan.md
│   ├── MAKER_WIDGET_GENERATION_PLAN.md   # Maker integration plan (tech + non-tech)
│   ├── MAKER_AND_MCP_DELIVERY_PLAN.md   # 5-week plan: hostable MCP + Maker widget service
│   ├── PLAN_WEEK1_PLATFORM_INTEGRATION.md   # Week 1 detailed plan, two-person split (MCP + Maker KT/contract)
│   ├── message-schemas.md
│   ├── discovery-agent-architecture.excalidraw
│   ├── generator-agent-architecture.excalidraw
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

| Method | Endpoint | Body / Query | Response |
|--------|----------|------|----------|
| GET | `/api/health` | — | `{ ok, has_api_key }` |
| GET | `/api/catalog` | `?library=untitledui\|metafore\|both` | `{ tokens, catalog }` — library-aware |
| POST | `/api/chat/stream` | `{ message, history, intent, library }` | SSE stream (status + thinking + chunk + done) |
| POST | `/api/chat` | `{ message, history }` | `{ content }` (non-streaming, GPT-4o) |
| POST | `/api/preview` | `{ code }` | Full HTML for iframe (with Tailwind config) |
| POST | `/api/generate` | `{ prompt }` | `{ code }` (Claude Sonnet) |
| POST | `/api/generate-variants` | `{ prompt, count, keywords }` | `{ variants }` (Claude Sonnet) |

### Streaming flow when `USE_LANGGRAPH=true`

1. `handle_stream()` parses `message`, `history`, `intent` (clean user query for classification), and `library` (active design system)
2. `_fast_classify(intent)` → returns "generate"/"discover"/"review"/"chat"
3. If `"chat"` → `_handle_direct_chat()` (GPT-4o-mini streaming + RAG context, fast)
4. If `"generate"/"discover"/"review"` → `_handle_langgraph_stream(message, history, workflow=..., library=...)` → `agent.server.run_agent_stream()`
5. SSE events: status → thinking (discovery/gen tokens, hidden in bar) → chunk (final response) → done

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
| `App` | Main state: conversations, streaming, agentStep, codeFiles, thinkingContent, **selectedLibrary** |
| `ThinkingBar` | Collapsible thinking bar with **text summary** of working/changes |
| `AgentPipeline` | Real-time pipeline visualization (5 nodes: Classify→Discovery→Generate→QA→Respond) |
| `Sidebar` | Conversation history + **library selector** (Untitled UI / Metafore / Both) |
| `WelcomeScreen` | Suggestion cards with multi-agent description |
| `MarkdownContent` | Renders markdown + highlight.js code blocks |
| `PreviewModal` | Fullscreen preview — single (with viewport switcher) or multi-variant |
| `InlinePreview` | Inline iframe preview + expand + code toggle |
| `MultiPreview` | Side-by-side variant grid |
| `Message` | User/assistant messages with ThinkingBar + **pinned file tags** |
| `InputArea` | Auto-growing textarea + **pinned context bar** showing attached files |
| `CodePanel` | Right panel: saved code files with **pin/attach system** (pinned section at top) |
| `FeaturesPanel` | Right panel: Quick Actions / Variants / Catalog tabs — **library-aware catalog fetch** |

### Library Switcher

- **`selectedLibrary` state** in App: `'untitledui'` | `'metafore'` | `'both'`
- **Sidebar selector**: Segmented control between header and conversations list
- **Passed through**: `streamChat()` POST body, `/api/catalog?library=` query, all agent pipeline calls
- **FeaturesPanel catalog tab**: Refetches components when library changes

### Code Pin/Attach System

- Each code file gets a **pin icon** (visible on hover, always visible when pinned)
- Pinned files float to the **top of the list** in a "PINNED" section
- **InputArea** shows a `pinned-context-bar` with chips for each pinned file
- **sendMessage** prepends pinned code as context: `IMPORTANT: You MUST use this pinned code as the base component to modify...`
- **Intent vs Message**: Clean user `intent` sent for classification, full context-enriched `message` sent to pipeline
- **Pinned tags** rendered in user chat messages for visibility
- **FeaturesPanel** quick actions and variant prompts dynamically reference `pinRef` ("the pinned component" vs "the last UI component")
- **Boilerplate instructions** (`CODE_RULE`) hidden from user-visible chat messages but sent to backend

### ThinkingBar (Cursor-style with text summary)

- During generation: pulsing "Thinking..." with discovery/generation output hidden
- After completion: "Thought for X lines" + **brief text summary** extracted from key phrases (component names, changes made)
- Thinking content saved per message (`thinkingContent` field)

### Chat State Management

- **`conversationsRef`**: Ref for latest conversations, avoids stale closures in `sendMessage`
- **`thinkingContent`**: Accumulates thinking tokens during streaming
- **`codeFiles`**: Array with `{ id, label, code, time, folder, context, pinned }` per file
- **History truncation**: Code blocks in history replaced with `[code block omitted]`, truncated to 500 chars
- **`displayText` vs `backendText`**: User sees clean message, backend receives enriched message with pinned context + code rules
- **`pinnedLabels`**: Stored per message for rendering pinned tags in chat

### Color Palette

Dark theme with violet accent (`--accent: #7c3aed`), subtle cool undertones:
- Backgrounds: `--bg: #09090b` → `--bg-sidebar: #0f0f14` → `--bg-chat: #16161d`
- Text: `--text: #f0f0f5` (warm white), `--text-muted: #6b6b80` (blue-gray)
- Borders: `--border: #2a2a38` (cool-toned)
- Status: green/red/orange with muted variants

### Code Extraction

- `extractBestRunnableCodeBlock()`: Scoring system prioritizes blocks with `root.render` (+50000) and PascalCase components (+30000)
- `extractAllRunnableCodeBlocks()`: For variant detection (multiple complete components)
- Streaming: Detects unclosed code fences and strips them to avoid rendering raw code

---

## 8. Design System Data (Multi-Library)

### Library File Mapping

| Library | Catalog File | Tokens File | Components | Brand Color |
|---------|-------------|-------------|-----------|-------------|
| `untitledui` | `catalog.json` | `tokens.json` | 24 | Blue (`#1570EF`) |
| `metafore` | `metafore_catalog.json` | `metafore_tokens.json` | 31 | Purple (`#7F56D9`) |
| `both` | Merged from both | Merged tokens | 55 | Both palettes |

### catalog.json — Untitled UI (24 components)

Each component includes `name`, `description`, `props`, `tailwind_pattern`, `variants`.

**Components:** Button, Input, Badge, Avatar, Card, Table, Tabs, Modal, Select, Checkbox, EmptyState, StatsCard, SearchInput, ProgressBar, Toggle, Radio, Textarea, Dropdown, Tooltip, Tag, Pagination, FileUpload, LoadingIndicator, Notification

### metafore_catalog.json — Metafore (31 components)

Same structure. Brand color is purple. Components span base (21), foundations (4), application (5), pages (1).

**Components:** Button, ButtonUtility, ButtonGroup, CloseButton, SocialButton, Input, InputGroup, Label, Checkbox, Select, MultiSelect, Combobox, Textarea, Badge, Avatar, Toggle, Tooltip, Slider, Dropdown, Tags, Progress, FeaturedIcon, DotIcon, RatingBadge, RatingStars, Pagination, Tabs, Table, EmptyState, LoadingIndicator, HomeScreen

### tokens.json / metafore_tokens.json

| Token | Untitled UI | Metafore |
|-------|------------|----------|
| Primary color | Blue (`primary→blue`) | Purple (`primary→purple`) |
| Color families | primary, gray, success, error, warning, purple, indigo, rose | primary, gray, success, error, warning |
| Font | Inter | Inter |
| Shadows | 5 levels (xs-xl) | 7 levels (xs-3xl) |
| Radius | 7 values | 9 values |
| tailwindMapping | `primary→blue` | `primary→purple` |

### coding_guidelines.md

Injected into Generator's prompt. Covers:
- PascalCase naming, function components only
- Tailwind CSS only (no inline styles)
- Accessibility: focus states, semantic HTML, aria-labels
- No imports (React/ReactDOM global via CDN)
- Component structure pattern
- Variant generation rules

---

## 9. Generator Prompt (Library-Aware)

The generator in `agent/generator.py` has library-specific system prompts cached per library (`_generation_prompt_cache`):

### Library-Specific Tailwind Patterns

| Pattern | Untitled UI | Metafore |
|---------|------------|----------|
| Primary button | `bg-blue-600 hover:bg-blue-700` | `bg-purple-600 hover:bg-purple-700` |
| Focus ring | `focus:ring-blue-500` | `focus:ring-purple-500` |
| Input focus | `focus:border-blue-500` | `focus:border-purple-500` |
| Toggle ON | `bg-blue-600` | `bg-purple-600` |
| Info badge | `bg-blue-50 text-blue-700` | `bg-purple-50 text-purple-700` |

Common patterns (cards, tables, badges, avatars, layout, typography, tabs, modals) are identical.

When `library="both"`, both pattern sets are included in the prompt.

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

## 11. RAG System Details (Library-Aware)

**File:** `agent/rag.py`

### How It Works
1. **Indexing** (`build_index(library)`): Per-library chunking — e.g., Untitled UI: 24 component + 6 token + ~12 doc chunks ≈ 42. Metafore: 31 + 5 + ~12 ≈ 48. Both: ~90 total.
2. **Embedding**: OpenAI `text-embedding-3-small` embeds all chunks into float32 vectors
3. **Storage**: `_stores` dict holds per-library `{chunks, embeddings, fingerprint}`
4. **Caching**: Embeddings saved as `embeddings_{library}_{fp}.npy` files in `.rag_cache/` with fingerprint-based invalidation
5. **Querying** (`query(text, k=3, library)`): Embeds the query, cosine similarity against library-specific chunks, returns top-k

### Injection Points
- **`chatbot/server.py` → `_handle_direct_chat()`**: RAG context injected as system message after main prompt
- **`agent/orchestrator.py` → `respond_node()` chat path**: RAG context injected with `library` param

---

## 12. Important Decisions & Gotchas

- **Claude Sonnet for code generation:** Generator uses `ChatAnthropic(model="claude-sonnet-4-20250514")`. Falls back to GPT-4o if `ANTHROPIC_API_KEY` is not set or credits are insufficient.
- **GPT-4o-mini for fast tasks:** Classification, discovery, and chat use GPT-4o-mini.
- **Pre-classification with intent separation:** Frontend sends `intent` (clean user query) for classification and `message` (enriched with pinned code + rules) for the pipeline. `_fast_classify(intent)` avoids being confused by long pinned code context.
- **Library-aware throughout:** `library` param flows from sidebar → `streamChat()` → `server.py` → `run_agent_stream()` → `OrchestratorState` → all nodes (discovery, generation, respond) → tools, RAG.
- **`set_active_library()`:** Called in `classify_node` to configure tools with the correct library before any tool calls.
- **Pinned code as explicit context:** `sendMessage` prepends a forceful instruction (`IMPORTANT: You MUST use this pinned code...`) to ensure the LLM prioritizes pinned files over conversation history.
- **`displayText` vs `backendText`:** User-facing messages are clean (no boilerplate instructions). Backend messages include `CODE_RULE` + pinned context.
- **Thinking vs Chunk events:** `agent/server.py` sends `{"type": "thinking"}` for discovery/generation tokens, `{"type": "chunk"}` only for final response.
- **No ReAct loops in Discovery/QA:** Discovery is a single GPT-4o-mini call. QA calls regex tools directly. Zero unnecessary LLM round-trips.
- **Per-library caching:** Discovery prompts, generator prompts, tokens, and RAG indexes are all cached per library key to avoid redundant loading.
- **RAG auto-rebuilds:** Per-library fingerprints check source file mtimes and rebuild when any file changes.
- **Multiple processes on port 3851:** On Windows, always kill old processes before restarting: `netstat -ano | Select-String ":3851"` then `taskkill /F /PID <pid>`

---

## 13. Recent Changes (Latest Session)

### Multi-Library Integration (Library Switcher)
1. **Metafore design system data** — Created `metafore_catalog.json` (31 components) and `metafore_tokens.json` (purple brand, full token set)
2. **Library selector UI** — Segmented control in sidebar (Untitled UI / Metafore / Both) with `selectedLibrary` state
3. **End-to-end library param** — `library` flows from frontend → `streamChat()` → `server.py` → `run_agent_stream()` → `OrchestratorState` → discovery/generator/RAG/tools
4. **Library-aware agent pipeline** — Discovery loads correct catalog, Generator uses library-specific Tailwind patterns (blue vs purple), RAG indexes per-library, tools load correct JSON files
5. **API catalog endpoint** — `/api/catalog?library=...` returns correct components (24 for untitledui, 31 for metafore, 55 for both)

### Pinned Code Context System
6. **Code file pinning** — Pin icon on hover in CodePanel, pinned files float to top in "PINNED" section
7. **Pinned context in chat** — Pinned file chips shown above textarea, pinned tags rendered in user messages
8. **Context injection** — Pinned code prepended to backend messages with forceful `IMPORTANT: You MUST use this pinned code...` instruction
9. **Intent vs message separation** — Clean `intent` for classification, enriched `message` for pipeline. Prevents classifier confusion from long pinned code.
10. **Dynamic quick action prompts** — `pinRef` references "the pinned component(s)" or "the last UI component" based on pin state

### UI/UX Improvements
11. **Color palette refresh** — Dark theme with violet accent (`#7c3aed`), cool undertones, better depth layering
12. **ThinkingBar text summary** — Extracts key phrases from thinking content for brief summary display
13. **Hidden boilerplate** — `CODE_RULE` instructions hidden from user-visible messages, only sent to backend
14. **Generator Agent diagram** — `docs/generator-agent-architecture.excalidraw`

### Previous Session
15. **Claude Sonnet code generation** with GPT-4o fallback
16. **Pre-classification optimization** — eliminates redundant classify LLM call
17. **Cursor-style ThinkingBar** — collapsible thinking bar for discovery/generation output
18. **SSE thinking events** — separate `thinking` vs `chunk` event types

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
4. **Agent changes:** Edit files in `agent/` directory — all are library-aware via `library` param
5. **Frontend changes:** Edit `chatbot/app.jsx` (React) and `chatbot/styles.css`
6. **Backend changes:** Edit `chatbot/server.py` for API routes (library-aware loading)
7. **Design system:** Edit `design_system/*.json` files. Use `catalog.json`/`tokens.json` for Untitled UI, `metafore_catalog.json`/`metafore_tokens.json` for Metafore. RAG auto-rebuilds per library.
8. **Adding a new library:** Add entries to `_LIB_FILES` dicts in `server.py`, `discovery.py`, `generator.py`, `tools.py`, `rag.py`. Create the catalog + tokens JSON files. Add the option to the sidebar selector in `app.jsx`.
9. **Dependencies:** `pip install -r requirements.txt`
10. **Kill old processes:** On Windows, always check `netstat -ano | Select-String ":3851"` and kill before restart

---

## 16. One-Line Summary

**Multi-agent design system chatbot (4 LangGraph agents + 6 tools + RAG + Claude Sonnet + GPT-4o-mini) with switchable design system libraries (Untitled UI 24 components / Metafore 31 components / Both), code pinning with explicit context injection, library-aware agent pipeline, Cursor-style thinking bar with text summaries, dark violet-accent UI, real-time pipeline visualization, inline live previews, and ChatGPT-style conversation UI.**
