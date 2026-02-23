# Milestone 1 — Design System Agent  
## Full Progress Report & Onboarding Document

**Document type:** Progress report + onboarding  
**Audience:** New joiners, stakeholders, and team members who need full context from day one to present  
**Last updated:** 23 February 2026  
**Scope:** From project inception through Week 1 (23–27 Feb 2026) of the Maker/MCP platform integration plan  

---

## Table of contents

1. [Document purpose and how to use it](#1-document-purpose-and-how-to-use-it)
2. [For newcomers: project at a glance](#2-for-newcomers-project-at-a-glance)
3. [Glossary and key terms](#3-glossary-and-key-terms)
4. [Meetings in serial order](#4-meetings-in-serial-order)
5. [Progress from day one (before the 4-agent architecture)](#5-progress-from-day-one-before-the-4-agent-architecture)
6. [4-agent architecture and tools](#6-4-agent-architecture-and-tools)
7. [Optimizations and UX improvements](#7-optimizations-and-ux-improvements)
8. [Multi-library support](#8-multi-library-support)
9. [Pinned code and UX polish](#9-pinned-code-and-ux-polish)
10. [Maker integration and hostable MCP (strategy and plans)](#10-maker-integration-and-hostable-mcp-strategy-and-plans)
11. [Week 1 — Platform integration (day-by-day plan)](#11-week-1--platform-integration-day-by-day-plan)
12. [Current status and next steps](#12-current-status-and-next-steps)
13. [References and related docs](#13-references-and-related-docs)

---

## 1. Document purpose and how to use it

This document serves two purposes:

- **Progress report:** It records what was done from the very start of the project (including the period before the 4-agent architecture) through the current state, in enough detail for stakeholders and new joiners to understand the evolution.
- **Onboarding:** It explains the project in plain language, lists meetings in order with key outcomes, and points to where to find more detail.

Use it when:

- You have just joined the team and need full context.
- You need to explain the project or its history to someone else.
- You need to recall what was decided in which meeting.
- You are preparing for Week 1 deliverables or handovers.

---

## 2. For newcomers: project at a glance

| Question | Answer |
|----------|--------|
| **What is this project?** | A multi-agent system that generates **production-quality React/JSX UI components** from natural language prompts, using our **design system** (Untitled UI and/or Metafore). |
| **What do we have today?** | A **4-agent LangGraph pipeline** (Orchestrator → Discovery → Generator → QA) with 6 tools and RAG, a ChatGPT-style chatbot UI, support for two design libraries (Untitled UI, Metafore, or both), and an MCP server that exposes the component library. |
| **What are we doing next?** | **Platform integration:** connect this engine to **Maker** (the platform where apps and dashboards are built) and make our **MCP server hostable** so Maker or the widget service can call it. Week 1 (23–27 Feb) focuses on knowledge transfer (KT), MCP spec, and contract v0. |
| **Who is involved?** | Two-person delivery team (Person A: MCP/service/APIs; Person B: Maker integration/review UX/runbook). Stakeholders include Bharat (architecture), Sivaraja (contract, KT), Brazen team (coding/design-system guidelines). |
| **Where is the code?** | `milestone1-agent/` — main app in `chatbot/` (UI + server), agents in `agent/`, design data in `design_system/`, docs in `docs/`. |
| **How do I run it?** | `cd milestone1-agent/chatbot && python server.py` → open http://localhost:3851. Set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `USE_LANGGRAPH=true` in `.env`. |

---

## 3. Glossary and key terms

| Term | Meaning |
|------|--------|
| **Maker** | The platform where apps are created from a Business Requirements Document (BRD); includes role-based dashboards (Pulse). We are adding **automated widget generation** for the Web channel. |
| **MCP (Model Context Protocol)** | A way to expose tools and resources to AI agents. Our **MCP server** exposes the component library (catalog + tokens) so Cloud Code or agents can list components, get specs, and get design tokens. |
| **Cloud Code** | Claude-based coding environment that can call our MCP server to generate UI using our design system (no Figma required for Milestone 1). |
| **Figma MCP** | Used by designers to get Figma screens/URLs as output. **We do not use Figma MCP for our generation flow**; we use prompt → Cloud Code + our MCP → component. |
| **Component library** | Our set of UI components (Untitled UI 24, Metafore 31, or both 55) with specs and Tailwind patterns. Stored as JSON (catalog + tokens); enterprise-level widget library will be per-tenant in Maker. |
| **Widget Manifest** | Structured response from our widget service: list of widgets (from library + newly generated) with IDs, code, version, QA/a11y results. |
| **Contract v0** | Agreed request/response shape for the widget generation API (e.g. POST /maker/generate-widgets, POST /maker/regenerate-widget). |
| **Hostable MCP** | MCP server that can be deployed (e.g. Docker), called at a URL, with health check and runbook. |
| **RAG** | Retrieval-augmented generation: we embed design-system chunks and inject relevant context into chat and discovery. |
| **STM / LTM** | Short-term memory (session context) and long-term memory (persisted, e.g. in DB). Referenced in architecture discussions for future state. |
| **KT** | Knowledge transfer — e.g. Maker KT to understand how Maker triggers “add widget,” what context it sends, and where the widget library lives. |

---

## 4. Meetings in serial order

The following meetings are listed in **chronological / logical order**. Each entry includes the **source file** (from Downloads), **attendees** (where identifiable), **main topics**, and **decisions or outcomes**. These meetings shaped the milestones, architecture, and Week 1 plan.

---

### Meeting 1 — Initial PoC plan (source: `innitial plan.txt`)

**Purpose:** Define the PoC for AI-assisted custom component generation.

**Main points:**

- **Goal:** Human-in-the-loop workflow: Prompt → AI (Claude) → Figma MCP → Code (Cursor) → Human Approval → Component Library.
- **In scope:** Use existing VARNAM 2.0 components when available; create new ones if needed; 1–2 component types; production-quality code; **mandatory human approval**.
- **Out of scope:** Full component coverage, zero-human approval, runtime UI generation.
- **Success:** End-to-end flow works; component follows design system; code needs minimal changes; component is added to the library; demo is clear.

**Note for newcomers:** This early plan mentioned Figma MCP. A later meeting (New recording 1) clarified that **our** flow uses **Cloud Code + our MCP server**, not Figma MCP, for Milestone 1.

---

### Meeting 2 — Kickoff and milestone split (source: `meet 1.txt`)

**Attendees:** Sathvik, Shan, team (Aditya, Vamsi, etc.).

**Main points:**

- Integration with Maker is the **last step**. First: get the **POC done**, then showcase “art of possibility,” then integrate with Maker.
- **MCP server access:** Get access from **Levins** (he manages the MCP server). Connect with Cloud Code and see how components are generated.
- **Three milestones agreed:**
  - **Milestone 1:** Generate the component (proof that we can generate using a simple prompt).
  - **Milestone 2:** Make the component perfect for our system (QA/validator, best practices, structure for 11/runtime, push to component library).
  - **Milestone 3:** Integrate with Maker (with help from Bharat and team).
- Work split: research and plan first; Sathvik to assist; hand over to backend team for integration later.
- **Timeline:** Team to propose timeline; culture of “same day or max 2 days” for delivery where applicable.

**Outcomes:** Clear order — M1 (generate) → M2 (quality + library) → M3 (Maker). MCP access from Levins. POC before integration.

---

### Meeting 3 — Cloud Code + our MCP (no Figma MCP); M1/M2/M3 clarified (source: `New recording 1.txt`)

**Attendees:** Bharat (Sean), team (Aditya, Vamsi, etc.).

**Main points:**

- **Critical clarification:** For our flow, we do **not** use **Figma MCP**. We use **Cloud Code connected to our MCP server**. Input = **simple prompt**. Output = **component**.
- **Figma MCP** is for designers (Figma screen → Figma URL). We need **front-end code**, not Figma design. Figma could be phase 2 as extra context.
- **Where to get MCP:** Ask **Levins** for access to **our** MCP server. If needed for POC, any open UI library with an MCP server can be used to prove the concept.
- **Milestone 1:** Cloud Code + our MCP server → generate component from prompt. That’s the proof.
- **Milestone 2:** QA/validator agent — check best practices, required structure, variables for runtime; then push to final repo (component library).
- **Milestone 3:** After M1 and M2 are done, integrate with Maker.

**Outcomes:** Architecture corrected: no Figma fetch; Cloud Code + our MCP only. M1/M2/M3 responsibilities clearly stated. Levins for MCP access.

---

### Meeting 4 — Architecture, coding guidelines, microservice, transport (source: `convo bharat.txt`)

**Attendees:** Bharat Kandappan, Aditya Anand, Kongala Vamsi, Shanmuga Sivaraja.

**Main points:**

- **Coding guidelines:** Add coding guidelines to the system; figure out how to add them (e.g. for QA and consistency).
- **Maker storage:** Aditya asked for KT on how Maker stores things; Bharat suggested to think through “what to do first” and to get KT when needed.
- **Architecture first:** “Developing is easy, architecting is difficult.” Draw a **diagram/sketch** of what you have in mind (Excalidraw or draw.io).
- **Microservice:** The widget/MCP service should be a **microservice**: its **own database**, **transport layer** (HTTP, gRPC, or Kafka — to be decided), and clear **message structure**.
- **STM/LTM:** Bharat referenced STM and LTM; offered to teach Alembic, DB handling, and how they use STM. Team to sketch first, then discuss.
- **Open API:** If we build a system that is Open API compatible, that can be useful (e.g. “Open Chat UA”–style).

**Outcomes:** Emphasis on ideation sketch and architecture before implementation. Microservice with own DB and transport (HTTP/gRPC/Kafka). Coding guidelines to be added. Sivaraja to add Bharat to the group for a single place of communication.

---

### Meeting 5 — LangGraph agents, tools, Fast MCP, quality (source: `convo bharat 13.txt`)

**Attendees:** Bharat Kandappan, Sivaraja, Aditya Anand, Kongala Vamsi.

**Main points:**

- **Build agents in LangGraph:** Create agents (e.g. “react agent”), add system prompt and **tools**. Use **Fast MCP client** in Python; pass the **streamable HTTP URL** from the Python MCP server — then those tools are accessible to the agent.
- **Sivaraja (requirements):**
  - One agent that **generates** the component.
  - **Tools:** (1) fetch from **existing component library**, (2) **refer primitives**, (3) merge as needed. Before creating the component, **verify quality** (best practices, same standards as front-end team when they manually create components).
  - Get the **document** from the **Brazen team** for design system and component library best practices — use it for the agent/QA.
- **Action:** Come back with **agent count** and **tool list** quickly; discuss again in the same group (Bharat included).

**Outcomes:** LangGraph + Fast MCP client + streamable HTTP URL for tools. One generate agent with tools: fetch from library, refer primitives, merge, then quality check. Brazen doc for coding/design-system guidelines. Align agent/tool list and reconvene.

---

### Meeting 6 — Maker KT: add widget flow, widget library, trace view (source: `plan platform integration.txt`)

**Attendees:** Shanmuga Sivaraja, Sugandha Jain, Aditya Anand, Kongala Vamsi.

**Main points:**

- **Clarity on Maker:** Sivaraja confirmed that Aditya and Vamsi have clarity on what Maker is and what has been achieved so far with Maker.
- **New feature:** “Add new widget” is a **new feature** being designed (not yet developed). It can impact the UI generator; that’s what the team wanted to showcase.
- **Trace view:** Similar to **Lang Smith** — show the complete trace of what happened behind the scenes. Team confirmed familiarity with Lang Smith.
- **Add widget — two options:**
  1. **Custom widget:** User says “add a new widget” to the pulse dashboard (e.g. for manager role). Maker suggests: add from **widget library** OR **create custom** by describing what you need (prompt). For custom: context + prompt template → user writes prompt → Maker AI creates widget → user can **approve** or **suggest changes**.
  2. **Widget library:** Open library of widgets (system/default + user-added). Hover/view details, **customize properties** (e.g. toggle fields on/off), then “add widget”; context is added and same flow.
- **Storage:** Widget/component library is at **enterprise level** (per tenant). Within that tenant, a user can use components **across different apps**.
- **Aditya’s question:** After adding custom widgets, are they saved per user or overall? **Answer:** Different users within the tenant can use the component across apps; saved at enterprise/tenant level.

**Outcomes:** Maker “add widget” flow (library vs custom) and review/approve flow understood. Trace view = Lang Smith–like. Widget library = enterprise-level, per-tenant. Plan platform integration doc and Week 1 plan align with this KT.

---

## 5. Progress from day one (before the 4-agent architecture)

### 5.1 Earliest phase: single-LLM design system chatbot

- **What existed:** A ChatGPT-style UI with **one LLM** (Claude) for both conversation and code generation. Design system lived in **static JSON**: `catalog.json` (components) and `tokens.json` (colors, typography, spacing). No agents, no routing, no QA.
- **Capabilities:** User could send a message and get a streaming reply; could ask to “generate” and receive React/JSX code. **Preview** (rendering code in an iframe with React + Babel + Tailwind) was available. Backend: simple Python HTTP server with SSE.
- **Data:** Only **Untitled UI** (24 components, blue brand). No library switcher, no Metafore, no RAG.
- **Why it matters:** This is the “day one” baseline. All later work (agents, tools, RAG, multi-library, Maker, MCP) builds on this.

### 5.2 Pre–LangGraph: tools and structure

- **Tools-like behavior:** The codebase supported “list components,” “get component spec,” and “get design tokens” for the LLM or the app (e.g. catalog UI). These became the **MCP-equivalent tools** in `agent/tools.py`.
- **Preview and quality:** Ability to preview generated code and basic quality/accessibility checks (PascalCase, Tailwind, no imports) existed or were added. These became **preview_component**, **verify_quality**, and **check_accessibility**.
- **Single path:** User prompt → LLM (Claude) → code → optional preview. No discovery step, no formal QA loop, no orchestration.

---

## 6. 4-agent architecture and tools

### 6.1 Orchestrator

- **LangGraph StateGraph** in `agent/orchestrator.py`: **classifies** the user request and **routes** to the right workflow: generate, discover, review, or chat.
- **State:** messages, workflow, user_request, discovery_output, generated_code, qa_result, retry_count, **library** (for multi-library support).

### 6.2 Discovery agent

- **File:** `agent/discovery.py`. Uses the **catalog** to suggest which components and **Tailwind patterns** fit the user’s request.
- **Implementation:** Single LLM call (GPT-4o-mini) with pre-loaded catalog — no ReAct loop.

### 6.3 Generator agent

- **File:** `agent/generator.py`. Uses **Claude Sonnet** to write complete React/JSX code.
- **System prompts** include exact Untitled UI (and later Metafore) Tailwind patterns for buttons, cards, tables, badges, etc.

### 6.4 QA Reviewer

- **Rule-based** (no LLM). Runs **verify_quality** and **check_accessibility**; returns PASS/FAIL. On FAIL, pipeline can **retry** generation (max 2 retries). Implemented in `agent/reviewer.py` and inline in the graph.

### 6.5 Six tools (library-aware)

| Tool | Purpose |
|------|---------|
| `list_components` | List components from the active library’s catalog |
| `get_component_spec` | Full spec + Tailwind patterns for one component |
| `get_design_tokens` | Colors, typography, spacing, shadows from tokens |
| `preview_component` | Save code as preview.html (React+Babel+Tailwind sandbox) |
| `verify_quality` | Rule-based: PascalCase, Tailwind, no imports, design-system compliance |
| `check_accessibility` | Rule-based: semantic HTML, aria-labels, focus states, contrast |

All in `agent/tools.py`; they use `set_active_library(library)` so the correct JSON files are loaded.

### 6.6 RAG

- **File:** `agent/rag.py`. In-memory vector store: chunks from catalog, tokens, and docs; **OpenAI text-embedding-3-small**; disk cache. Injected into chat and (where relevant) discovery.
- **Per-library:** Separate indexes per library; when `library="both"`, chunks from both design systems are indexed.

### 6.7 Streaming and UI

- Backend sends **SSE** events: status (“Analyzing…”, “Searching component library…”, “Generating…”, “Reviewing…”), then thinking/chunk/done/error.
- Frontend shows pipeline: Classify → Discovery → Generate → QA → Respond.

---

## 7. Optimizations and UX improvements

### 7.1 Pre-classification

- **Problem:** Orchestrator’s classify node used an LLM call even when the frontend could infer intent → redundant ~1–2 s call.
- **Change:** In `chatbot/server.py`, **`_fast_classify()`** (GPT-4o-mini) returns "generate" | "discover" | "review" | "chat". This is passed as **workflow** so **classify_node skips** its LLM call.
- **Intent vs message:** Frontend sends clean **intent** for classification and possibly **enriched message** (e.g. with pinned code) to the pipeline.

### 7.2 Claude Sonnet and fallback

- **Code generation:** Claude Sonnet (`claude-sonnet-4-20250514`) via Anthropic SDK. Fallback to GPT-4o if API key missing or credits insufficient.
- **Classification / chat / discovery:** GPT-4o-mini for speed and cost.

### 7.3 SSE: thinking vs chunk

- **`thinking`** events: discovery/generation tokens (shown in collapsible ThinkingBar).
- **`chunk`** events: final response only (shown in chat). Keeps the chat clean.

### 7.4 Cursor-style ThinkingBar

- Collapsible bar: “Thinking…” during generation; after completion, a short **text summary** (e.g. component names, changes). Thinking content stored per message.

---

## 8. Multi-library support

### 8.1 Design system data

- **Metafore added:** `metafore_catalog.json` (31 components), `metafore_tokens.json` (purple brand). Same structure as Untitled UI.
- **Mapping:**  
  - `untitledui` → catalog.json, tokens.json (24, blue).  
  - `metafore` → metafore_catalog.json, metafore_tokens.json (31, purple).  
  - `both` → merged (55 components).

### 8.2 Library switcher and end-to-end `library` param

- **UI:** Sidebar selector: Untitled UI / Metafore / Both.
- **Flow:** `library` from frontend → `streamChat()` → `chatbot/server.py` → `run_agent_stream()` → OrchestratorState → every node, tools, and RAG.
- **Tools:** `set_active_library(library)` in classify_node; tools load correct JSON (or merged for “both”).
- **RAG:** Per-library indexes and caches.
- **Generator:** Library-specific Tailwind patterns (e.g. blue vs purple).
- **API:** `GET /api/catalog?library=untitledui|metafore|both` returns 24, 31, or 55 components.

---

## 9. Pinned code and UX polish

### 9.1 Code pin/attach

- **Pin icon** on each code file; pinned files in a “PINNED” section at the top of the code panel.
- **Pinned context bar** above input; **pinned tags** in user messages.
- **Context injection:** Pinned code prepended with a strong instruction so the LLM prioritizes it. **Intent** (clean) used for classification; **message** can include pinned code + rules.

### 9.2 Quick actions and boilerplate

- Quick actions refer to “the pinned component(s)” or “the last UI component” based on pin state.
- CODE_RULE-style boilerplate hidden from user but sent to backend.

### 9.3 UI/UX

- Dark theme with **violet accent** (`#7c3aed`). ThinkingBar text summary. Generator Agent diagram in `docs/generator-agent-architecture.excalidraw`.

---

## 10. Maker integration and hostable MCP (strategy and plans)

### 10.1 Maker Widget Generation Plan

- **Goal:** Connect our UI generation engine to **Maker** so role-based dashboards get **auto-generated, design-system–compliant widgets** for the **Web** channel only (no UI for Voice/WhatsApp).
- **Flow:** User in Maker → “Create dashboard for [role]…” → Maker sends context (channel, roles, sections, design system) → **Adapter** checks Web → if Web: library match + pipeline for gaps → **Widget Manifest** → Maker “Review Widgets” (preview, approve/reject) → approved widgets registered.
- **Doc:** `docs/MAKER_WIDGET_GENERATION_PLAN.md`: 5-week timeline, RACI, risks, contract outline.

### 10.2 Hostable MCP and 5-week delivery plan

- **Requirement:** Host an **MCP server** for the component library that is **deployable** and callable by Maker or the widget service.
- **Current MCP:** Root `server.py` (FastMCP): `list_components`, `get_component_spec`, `get_design_tokens`, resources `design-system://tokens` and `design-system://components`; Untitled UI only; streamable HTTP (e.g. port 8000).
- **Target:** Library-aware (untitledui | metafore | both), **hostable** (Docker, health/readiness, runbook), same tools/resources with optional `library` param.
- **Doc:** `docs/MAKER_AND_MCP_DELIVERY_PLAN.md`: 5 weeks (23 Feb – 27 Mar 2026), week-by-week MCP + Maker deliverables, success criteria.

### 10.3 Contract v0 (summary)

- **POST /maker/generate-widgets**  
  **In:** channel, entryPoint, roles, pulseSections, designSystem (metafore | untitledui | both), optional brdText, existingWidgets, widgetLibrary, etc.  
  **Out:** skipped + skipReason when not Web; else widgets[] (id, name, source, code, version, qaResult, a11yResult), metrics, auditLog.
- **POST /maker/regenerate-widget**  
  **In:** widgetId, priorCode, reviewerNotes, makerContext.  
  **Out:** Updated widget with new version.

---

## 11. Week 1 — Platform integration (day-by-day plan)

Week 1 (23–27 Feb 2026): **KT + MCP spec + contract v0**.  
**Person A:** MCP scope, host strategy, architecture sketch. **Person B:** Maker KT, contract v0, coding guidelines ask, ideation sketch.  
**Doc:** `docs/PLAN_WEEK1_PLATFORM_INTEGRATION.md`.

| Day | Date | Person A | Person B | Sync |
|-----|------|----------|----------|------|
| **1** | Mon 23 Feb | MCP scope (tools, resources, library param); host strategy (Docker/cloud, URL, health). | Maker KT prep (questions, schedule); contract v0 draft (request/response from MAKER_AND_MCP_DELIVERY_PLAN). | 15 min: align MCP scope and contract v0; confirm KT timing. |
| **2** | Tue 24 Feb | Architecture sketch (microservice, DB, transport, MCP, agents/tools); finalize MCP scope doc. | Attend Maker KT; capture add-widget flow, payload, widget schema, review flow, enterprise library. Request coding guidelines from Brazen; document source. | 15 min: KT highlights (B); architecture sketch (A). |
| **3** | Wed 25 Feb | Propose agent count and tool list (e.g. one generate agent + tools: library fetch, primitives, quality); align with LangGraph, Fast MCP, streamable HTTP. | Contract v0 final (incorporate KT); ideation sketch: Maker → add widget (library/custom) → our service (MCP + agent) → component → review/approve → library. | 15 min: align agent/tool list with contract v0; resolve open KT questions. |
| **4** | Thu 26 Feb | Consolidate MCP scope + host strategy into “MCP spec” for sign-off; runbook outline (local, Docker, env vars). | Consolidate KT notes + contract v0 into “Maker integration contract v0”; assumptions and open points. Stakeholder review (both). Prep 1–2 slides for Friday. | Share MCP spec and contract v0 + KT summary with Sivaraja/Bharat; incorporate feedback. |
| **5** | Fri 27 Feb | — | — | **Friday demo:** MCP spec, contract v0, architecture sketch, ideation sketch, KT summary. **Sign-off** on MCP spec and contract v0. **Handover:** Person A (MCP impl); Person B (widget endpoint stub, Review UI prototype). |

### Week 1 deliverables checklist

| # | Deliverable | Owner |
|---|-------------|--------|
| 1 | MCP scope doc (tools, resources, library param) | Person A |
| 2 | MCP host strategy (Docker, URL, runbook outline) | Person A |
| 3 | Architecture sketch — backend microservice + MCP + transport | Person A |
| 4 | Agent/tool list (generate agent + tools: library fetch, primitives, quality) | Person A |
| 5 | Maker KT notes (add widget flow, payload, widget schema, review) | Person B |
| 6 | Contract v0 (generate-widgets + regenerate-widget request/response) | Person B |
| 7 | Coding guidelines source (Brazen) requested and documented | Person B |
| 8 | Ideation sketch — Maker → service → component library flow | Person B |
| 9 | KT sign-off + contract v0 approved | Both |
| 10 | Week 2 handover (Person A / Person B ownership) | Both |

---

## 12. Current status and next steps

### 12.1 Done (implemented and in use)

- 4-agent LangGraph pipeline (Orchestrator, Discovery, Generator, QA); 6 tools; RAG; all library-aware.
- Pre-classification; Claude Sonnet with GPT-4o fallback; SSE (thinking vs chunk); ThinkingBar with text summary.
- Multi-library (Untitled UI, Metafore, Both); library switcher; end-to-end `library` param.
- Pinned code (pin/attach, context bar, intent vs message, injection).
- Dark violet-accent UI; pipeline visualization; inline previews; code pinning; catalog tab.
- MCP server (root `server.py`): list_components, get_component_spec, get_design_tokens, resources; Untitled UI only; streamable HTTP.
- Documentation: PROJECT_CONTEXT.md, architecture.md, Maker and MCP plans, Week 1 plan, plan_bundle_for_llm, Excalidraw diagrams.

### 12.2 In progress / planned

- **Week 1 (23–27 Feb):** Execute day-by-day tasks above; stakeholder review; Friday demo; sign-off; Week 2 handover.
- **Week 2 onward:** MCP library-aware implementation; Docker/runbook; POST /maker/generate-widgets stub + channel gating; Review UI prototype; then Maker adapter, MCP deployment, governance, pilot readiness (see MAKER_AND_MCP_DELIVERY_PLAN).

### 12.3 Milestone roadmap

| Milestone | Status | Description |
|-----------|--------|-------------|
| **M1: Local LangGraph** | ★ CURRENT | 4 agents, 6 tools, RAG, Claude Sonnet + GPT-4o-mini, multi-library, pinning, ChatGPT-style UI. |
| **M2: Ctrlagent Maker** | PLANNED | Migrate agents to Maker platform; MCP server tools; Keycloak auth. |
| **M3: Production** | PLANNED | Pulse dashboards, PostgreSQL persistence, full deployment. |

---

## 13. References and related docs

| Document | Location | Purpose |
|----------|----------|---------|
| Full project context | `PROJECT_CONTEXT.md` | Run instructions, architecture, decisions, gotchas — use for new Cursor sessions and handoffs. |
| Maker Widget Generation Plan | `docs/MAKER_WIDGET_GENERATION_PLAN.md` | What we’re building, flow, 5-week timeline, RACI, risks, API contract. |
| Maker and MCP delivery plan | `docs/MAKER_AND_MCP_DELIVERY_PLAN.md` | 5-week plan with hostable MCP; week-by-week MCP + Maker deliverables; success criteria. |
| Week 1 platform integration | `docs/PLAN_WEEK1_PLATFORM_INTEGRATION.md` | Day-by-day tasks for Person A and Person B; deliverables checklist; naming. |
| Architecture | `docs/architecture.md` | Current and proposed architecture; transport (HTTP/gRPC/Kafka); DB; Maker mapping. |
| Plan bundle for LLM | `docs/plan_bundle_for_llm/` | 00_INDEX + 01–04: merged plan and context for external LLMs or professional doc generation. |
| Project context summary | `docs/plan_bundle_for_llm/04_PROJECT_CONTEXT_SUMMARY.md` | Short context: 4-agent pipeline, tools, RAG, Maker, team, key terms. |

---

### Meeting source files (referenced in Section 4)

- `C:\Users\adity\Downloads\innitial plan.txt` — Initial PoC plan (AI + Figma MCP + human approval).
- `C:\Users\adity\Downloads\meet 1.txt` — Kickoff with Sathvik; 3 milestones; MCP access from Levins.
- `C:\Users\adity\Downloads\New recording 1.txt` — Cloud Code + our MCP (no Figma MCP); M1/M2/M3 clarified.
- `C:\Users\adity\Downloads\convo bharat.txt` — Architecture, coding guidelines, microservice, transport, STM/LTM.
- `C:\Users\adity\Downloads\convo bharat 13.txt` — LangGraph agents, Fast MCP, tools, quality, Brazen doc.
- `C:\Users\adity\Downloads\plan platform integration.txt` — Maker KT: add widget flow (library vs custom), trace view, enterprise widget library.

---

*End of document. For questions or updates, align with the same stakeholder group (Bharat, Sivaraja) and update this doc and PROJECT_CONTEXT.md as needed.*
