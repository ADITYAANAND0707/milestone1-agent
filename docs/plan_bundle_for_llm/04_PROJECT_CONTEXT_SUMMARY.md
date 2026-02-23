# Project Context Summary (for LLM)

**Project:** Milestone 1 — Design System Agent  
**Purpose:** Multi-agent system that generates production-quality React/JSX UI components from natural language, using design systems Untitled UI, Metafore, or Both.

---

## Architecture (short)

- **4-agent pipeline:** Orchestrator → Discovery → Generator → QA (LangGraph).
- **6 tools:** list_components, get_component_spec, get_design_tokens (MCP-equivalent), preview_component, verify_quality, check_accessibility. All library-aware.
- **RAG:** In-memory vector store (OpenAI embeddings), per-library indexes; design-system chunks.
- **Design data:** `design_system/catalog.json`, `tokens.json`, `metafore_catalog.json`, `metafore_tokens.json`. Metafore 31 components, Untitled UI 24; "both" = 55 merged.
- **MCP server:** FastMCP `server.py` exposes component library over streamable HTTP (port 8000). Target: make it hostable (Docker, library param, health endpoint).

---

## Maker integration (what the plans describe)

- **Maker:** Platform where apps are built from a BRD; includes role-based dashboards. We add **automated widget generation** for the **Web** channel only.
- **Maker Adapter:** Thin layer: channel check (Web vs Voice/WhatsApp), context parsing, schema mapping. Non-Web → skip; Web → call widget service.
- **Widget service:** POST /maker/generate-widgets, POST /maker/regenerate-widget. Returns Widget Manifest (library + generated widgets, QA/a11y). Review flow in Maker before widgets are registered.
- **Contract v0:** Request fields (channel, roles, pulseSections, designSystem, etc.); response (skipped + skipReason, or widgets[], metrics, auditLog).

---

## Team and timeline

- **Two-person team:** Person A (service/APIs/MCP/quality), Person B (Maker integration/review UX/runbook).
- **5 weeks:** 23 Feb – 27 Mar 2026. Week 1: KT + MCP spec + contract v0. Weeks 2–3: MCP hostable + Maker hook. Weeks 4–5: Governance, pilot readiness.
- **Stakeholders:** Bharat, Sivaraja (architecture, contract, KT). Brazen team (coding/design-system guidelines).

---

## Key terms

| Term | Meaning |
|------|--------|
| Widget Manifest | Structured list of widgets (library + generated) with IDs, code, version, QA/a11y results. |
| Library-first | Reuse pre-approved widgets from library; generate only gaps. |
| Contract v0 | Agreed request/response shape for widget generation API. |
| Hostable MCP | MCP server deployable (Docker), callable at a URL, with health check and runbook. |
| Review Widgets | Maker UX: preview, approve, reject, or request changes before registering widgets. |

---

Use this summary with the numbered plan files (01–03) to produce a single professional document or prompt.
