# Week 1 — Platform Integration Plan (Detailed)

**Scope:** Week 1 only | Two-person team (Person A, Person B)  
**Dates:** 23–27 Feb 2026  
**Context:** Maker widget flow + hostable MCP for component library; align with LangGraph agents, Fast MCP, Cloud Code, and Maker KT.  
**Naming:** Matches project usage — MCP server, component library, agents, tools, Maker, contract v0, architecture sketch (Excalidraw/draw.io).

---

## Week 1 objective

- **Person A:** MCP server scope and spec; host/deploy strategy; architecture sketch (backend microservice + transport + MCP).
- **Person B:** Maker KT and contract v0; coding guidelines and design-system doc ask; ideation sketch (Excalidraw/draw.io) for integration flow.
- **Joint:** KT sign-off; MCP spec + contract v0 approved by end of week.

---

## Work distribution (two persons)

| Owner   | Focus area              | Key deliverables |
|---------|--------------------------|------------------|
| **Person A** | MCP server + backend architecture | MCP scope doc; library param design; host strategy; architecture diagram (microservice, DB, transport). |
| **Person B** | Maker integration + contract + UX flow | Maker KT notes; contract v0 (request/response); coding guidelines source; ideation sketch (integration flow). |

---

## Day-by-day plan (detailed)

### Day 1 — Monday (23 Feb)

| Task | Owner   | Detail |
|------|--------|--------|
| **MCP scope** | Person A | Document MCP scope: tools (list_components, get_component_spec, get_design_tokens, optional generate_ui); resources (design-system://tokens, design-system://components). Decide library param (untitledui / metafore / both) — tool arg vs query. |
| **Host strategy** | Person A | Decide how MCP will be hosted: Docker on shared host vs cloud; port and base URL; streamable-http only or health endpoint. One-page “MCP host strategy” with options and recommendation. |
| **Maker KT prep** | Person B | Prepare KT questions: how Maker triggers “add widget” (from library vs custom prompt); what context Maker sends; where widget library lives (enterprise-level); trace view (Lang Smith–like) if relevant. Book/schedule Maker KT session with platform owner. |
| **Contract v0 draft** | Person B | Draft request/response for “widget generation” API: required fields (channel, roles, pulseSections, designSystem); response (skipped vs widgets[]). Use existing MAKER_AND_MCP_DELIVERY_PLAN contract section as base. |
| **Sync** | Both | 15 min: align on MCP scope and contract v0 draft; confirm KT timing. |

---

### Day 2 — Tuesday (24 Feb)

| Task | Owner   | Detail |
|------|--------|--------|
| **Architecture sketch (backend)** | Person A | Draw architecture: microservice for widget/MCP (own DB, transport layer — HTTP/gRPC/Kafka per Bharat’s guidance). Show MCP server, component library access, and where agents/tools sit. Use Excalidraw or draw.io. |
| **MCP scope doc final** | Person A | Finalize MCP scope doc: base URL, transport (streamable-http), tools list, how library is passed. Share with Person B and stakeholder. |
| **Maker KT** | Person B | Attend Maker KT. Capture: dashboard “add widget” flow (library vs custom); payload Maker can send; widget schema Maker expects; review/approve flow; enterprise-level component library storage. |
| **Coding guidelines** | Person B | Request design-system and component-library best-practices doc from Brazen team (per Sivaraja). Document “coding guidelines” source and how it will be used (e.g. QA agent, prompt injection). |
| **Sync** | Both | 15 min: Person B shares KT highlights; Person A shares architecture sketch. |

---

### Day 3 — Wednesday (25 Feb)

| Task | Owner   | Detail |
|------|--------|--------|
| **Agent/tool count** | Person A | Propose agent count and tool list: e.g. one “generate component” agent with (1) tool to fetch from component library (via MCP), (2) tool to refer primitives, (3) merge + quality step. Align with Sivaraja/Bharat guidance (LangGraph, Fast MCP client, streamable HTTP URL). |
| **Contract v0 final** | Person B | Incorporate KT findings into contract v0. Finalize: POST /maker/generate-widgets and POST /maker/regenerate-widget request/response; Web-only gating field. One-page contract v0. |
| **Ideation sketch (integration)** | Person B | Sketch end-to-end flow: User in Maker → “add widget” (library or custom) → context + prompt → our service (MCP + agent) → component → review/approve → save to component library (enterprise). Excalidraw or draw.io. |
| **Sync** | Both | 15 min: align agent/tool list with contract v0; resolve open KT questions. |

---

### Day 4 — Thursday (26 Feb)

| Task | Owner   | Detail |
|------|--------|--------|
| **MCP spec + host strategy review** | Person A | Consolidate MCP scope doc and host strategy into single “MCP spec” for sign-off. Add: runbook outline (how to run locally, Docker, env vars). |
| **Contract v0 + KT notes review** | Person B | Consolidate KT notes and contract v0 into “Maker integration contract v0” doc. List assumptions and open points. |
| **Stakeholder review** | Both | Share MCP spec (Person A) and contract v0 + KT summary (Person B) with Sivaraja/Bharat. Incorporate feedback. |
| **Prep for Friday demo** | Both | Prepare 1–2 slide or one-pager: Week 1 outcomes (MCP spec, contract v0, architecture sketch, ideation sketch, KT sign-off). |

---

### Day 5 — Friday (27 Feb)

| Task | Owner   | Detail |
|------|--------|--------|
| **Friday demo** | Both | Present: MCP spec (scope, library param, host strategy); contract v0 (request/response, Web gating); architecture sketch (backend + MCP); ideation sketch (Maker → service → component library); KT summary. |
| **Sign-off** | Both | Get explicit sign-off on MCP spec and contract v0. Log decisions (naming, library param, transport). |
| **Handover to Week 2** | Both | Document: what Person A owns for Week 2 (MCP implementation); what Person B owns (widget endpoint stub, Review UI prototype). Update MAKER_AND_MCP_DELIVERY_PLAN or backlog. |

---

## Deliverables checklist (end of Week 1)

| # | Deliverable | Owner   | Status |
|---|-------------|--------|--------|
| 1 | MCP scope doc (tools, resources, library param) | Person A | |
| 2 | MCP host strategy (Docker, URL, runbook outline) | Person A | |
| 3 | Architecture sketch — backend microservice + MCP + transport | Person A | |
| 4 | Agent/tool list (generate agent + tools: library fetch, primitives, quality) | Person A | |
| 5 | Maker KT notes (add widget flow, payload, widget schema, review) | Person B | |
| 6 | Contract v0 (generate-widgets + regenerate-widget request/response) | Person B | |
| 7 | Coding guidelines source (Brazen doc) requested and documented | Person B | |
| 8 | Ideation sketch — Maker → service → component library flow | Person B | |
| 9 | KT sign-off + contract v0 approved | Both | |
| 10 | Week 2 handover (Person A / Person B ownership) | Both | |

---

## Naming and references (from transcripts)

- **MCP server** — Our hostable server exposing component library (catalog + tokens); Fast MCP, streamable HTTP.
- **Component library** — Enterprise-level; catalog/tokens (Untitled UI / Metafore); stored per tenant.
- **Agents / tools** — LangGraph agents; tools include fetch from component library (via MCP) and refer primitives; quality check before component creation.
- **Cloud Code** — Connected to our MCP server; prompt → component using our design system (Milestone 1 proof).
- **Maker** — Platform; “add widget” from library or custom (prompt); context + prompt template; review/approve; widget library (system + user).
- **Contract v0** — Request/response shape for widget generation API (channel, roles, pulseSections, designSystem, etc.).
- **Architecture sketch / ideation sketch** — Excalidraw or draw.io; microservice, DB, transport, messages (Bharat); integration flow (Maker → service → library).

---

## Sync and communication

- **Daily:** 15-min sync (progress, blockers, next day).
- **Stakeholder:** Use same group (Bharat, Sivaraja) for architecture and contract review; share sketches and docs in one place.
- **Decisions:** Log in a short “Week 1 decision log” (naming, library param, host choice, contract fields).

---

*Plan aligns with: plan platform integration.txt, convo bharat 13.txt, convo bharat.txt, New recording 1.txt, and MAKER_AND_MCP_DELIVERY_PLAN.md.*
