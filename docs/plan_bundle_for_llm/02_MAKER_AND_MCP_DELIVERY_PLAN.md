# Maker Widget Generation + Hostable Component Library MCP — Delivery Plan

**Scope:** 5 weeks | Two-person team  
**Change:** Requirement added — **host an MCP server for the component library** that is deployable and callable by Maker or the widget service.  
**Timeline:** 23 Feb – 27 Mar 2026

---

## At a glance

| Deliverable | Summary |
|-------------|--------|
| **Hostable MCP server** | Component library (catalog + tokens) exposed via MCP over HTTP; library-aware (Untitled UI / Metafore / Both); containerized and deployable. |
| **Widget generation service** | REST API for Maker: generate/regenerate widgets; Web-only gating; Widget Manifest; uses pipeline (and optionally MCP for catalog/tokens). |
| **Maker integration** | Adapter connects Maker to our service; review flow; optional: Maker or pipeline calls our MCP for design-system context. |

---

## Weekly timeline (to the point)

| Week | Dates | Focus | MCP deliverables | Maker/widget deliverables | Friday demo |
|------|--------|--------|-------------------|---------------------------|-------------|
| **1** | 23–27 Feb | KT + MCP spec + contract | MCP scope doc; library param design (untitledui/metafore/both); host/deploy strategy | Maker KT; contract v0 (request/response) | KT sign-off; MCP spec + contract v0 approved |
| **2** | 2–6 Mar | MCP hostable + vertical slice | MCP server library-aware; health endpoint; Docker + runbook; hostable on one env | POST /maker/generate-widgets stub + channel gating; Review UI prototype | MCP callable (e.g. from Postman/Claude); E2E Web vs Voice |
| **3** | 9–13 Mar | MCP in pipeline + Maker hook | Pipeline (or adapter) uses MCP for catalog/tokens when available; MCP deployed to target host | Maker adapter calls widget service; Review Widgets from real response | Maker triggers service; optional: pipeline uses MCP |
| **4** | 16–20 Mar | Governance + quality | MCP stability (timeouts, errors); version/health in response | Regenerate single widget; audit; QA/a11y gates; metrics | Iterate and regen; MCP stable |
| **5** | 23–27 Mar | Pilot ready | MCP runbook; env checklist; monitoring/alerting basics | Runbook; stakeholder pack; dress rehearsal | Pilot-ready + MCP hostable |

---

## 1. MCP server — what "hostable" means

- **Today:** `server.py` (FastMCP) exposes `list_components`, `get_component_spec`, `get_design_tokens`, resources for tokens/components. Uses only `catalog.json` and `tokens.json` (Untitled UI). Runs streamable-http on port 8000.
- **Target:**
  - **Library-aware:** Support `library` (untitledui | metafore | both). Load `catalog.json` / `metafore_catalog.json` and merge when both.
  - **Hostable:** Run in a way others can call it: Docker image, configurable host/port, health/readiness endpoint, clear runbook. Deploy to at least one environment (e.g. QA or internal host).
  - **Contract:** Same tools/resources; add optional `library` to tools so callers get the right design system.

---

## 2. Week-by-week plan (detail)

### Week 1 (23–27 Feb)

**MCP**
- Decide MCP scope: tools + resources only, or also a "generate_ui" helper. Confirm library param (query vs tool arg).
- Document: MCP base URL, transport (streamable-http), tools list, how `library` is passed.
- Decide host strategy: Docker on shared host, or cloud (e.g. one VM/container per env).

**Maker**
- Maker KT: how dashboard creation is triggered; sample request; widget schema; review/registration.
- Contract v0: POST /maker/generate-widgets request/response; POST /maker/regenerate-widget.

**Exit:** MCP spec + contract v0 agreed; host strategy chosen.

---

### Week 2 (2–6 Mar)

**MCP**
- Implement library-aware loading in MCP: `library` param on tools/resources; load `catalog`/`tokens` or `metafore_catalog`/`metafore_tokens` or merged.
- Add a health/readiness endpoint (e.g. GET /health or MCP-internal) so deployers can check liveness.
- Add Dockerfile (and optional docker-compose) for the MCP server; document PORT/HOST and env vars.
- Runbook: how to run locally; how to build and run the container; how to verify (e.g. list_components with library=metafore).

**Maker**
- Implement POST /maker/generate-widgets: channel gating (non-Web → skip); stub manifest for Web.
- Review Widgets UI prototype (can be minimal).

**Exit:** MCP is library-aware and runnable in Docker; widget endpoint returns skip or stub manifest; E2E demo Web vs Voice.

---

### Week 3–5 (summary)

- **Week 3:** Deploy MCP; Maker adapter calls widget service; Review Widgets from real response.
- **Week 4:** MCP stability; regenerate single widget; audit; QA/a11y gates; metrics.
- **Week 5:** MCP runbook final; pilot runbook; stakeholder pack; dress rehearsal.

---

## 3. MCP scope (concrete)

| Item | Detail |
|------|--------|
| **Transport** | Streamable HTTP (existing). Keep port configurable (e.g. 8000 default, env override). |
| **Tools** | `list_components(library?)`, `get_component_spec(component_name, library?)`, `get_design_tokens(library?)`. Optional: `generate_ui(prompt)` — if kept, add library. |
| **Resources** | `design-system://tokens` and `design-system://components`; support library via URI param or document "call tools with library". |
| **Hosting** | Docker image; run on single host or container platform; health endpoint; runbook. |
| **Data** | Read from `design_system/`: catalog.json, tokens.json, metafore_catalog.json, metafore_tokens.json. No DB. |

---

## 4. Success criteria (end of Week 5)

| Area | Criteria |
|------|----------|
| **MCP** | MCP server is library-aware, runs in Docker, is deployed and callable at a stable URL; runbook and health check in place. |
| **Widget service** | POST generate-widgets and regenerate-widget work; Web-only; manifest with library + generated widgets; review flow. |
| **Maker** | Maker can trigger the widget service (via adapter); Review Widgets shows real data; optional: Maker or pipeline uses MCP for component library. |

---

*Plan v1 — incorporates hostable Component Library MCP into the 5-week Maker Widget Generation delivery.*
