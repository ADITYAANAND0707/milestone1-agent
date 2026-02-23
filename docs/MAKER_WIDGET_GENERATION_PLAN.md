# Maker Web Channel UI Widget Generation — Plan Overview

**Audience:** Product, design, engineering, leadership  
**Scope:** 5-week delivery (23 Feb – 27 Mar 2026) | Two-person team  
**Status:** Plan v2.0 (rectified)

---

## At a glance

| Question | Answer |
|----------|--------|
| **What** | Connect our existing UI generation engine to Maker so role-based dashboards get auto-generated, design-system–compliant widgets (Web channel only). |
| **Why** | Maker creates apps from a BRD; we add automated widget generation with review and reuse so dashboards are consistent and fast to build. |
| **How** | A thin “Maker Adapter” calls our widget service; the service runs our 4-agent pipeline, returns a Widget Manifest (library + new widgets), and Maker shows a review flow before registering widgets. |
| **When** | 5 weeks. Week 1: understand Maker + lock contract. Weeks 2–3: working service + Maker hook. Weeks 4–5: governance, metrics, pilot readiness. |
| **Who** | Person A: service/APIs/quality. Person B: Maker integration/review UX/runbook. |

---

## 1. What we’re building (plain language)

- **Maker** is the platform where apps are created from a Business Requirements Document (BRD): goals, data, agents, tools, and **role-based dashboards**.
- Today, dashboard **widgets** (e.g. KPI cards, tables, search) are either hand-built or missing. We’re adding **automated widget generation** that:
  - Runs only for **Web** channel (no UI for Voice/WhatsApp).
  - Reuses **pre-approved widgets** from a library when possible.
  - **Generates new widgets** when there’s no match, using our design-system–aware engine.
  - Delivers a **review step** (preview, approve/reject/request changes) before widgets go into the app.
- Outcome: dashboards get a full set of widgets quickly, with consistent look (Metafore/Untitled UI) and quality/accessibility checks.

---

## 2. How it works (high level)

```
User in Maker: "Create a dashboard for [role] to display [description]"
        ↓
Maker sends context (channel, roles, sections, design system, etc.)
        ↓
Our adapter checks: Is this Web? → If no: skip and return a clear message.
        ↓
If Web: Check widget library for matches → reuse what exists.
        ↓
For anything not in library: run our generation pipeline (discovery → code gen → QA/a11y).
        ↓
Return a "Widget Manifest" (list of widgets: from library + newly generated, with quality results).
        ↓
Maker shows "Review Widgets": preview, approve, reject, or request changes.
        ↓
Approved widgets are registered; "Save and Deploy" creates a checkpoint.
```

**Rule:** UI generation happens **only for Web**. Voice and WhatsApp get a clear “skipped” response, no pipeline call.

---

## 3. Priorities (what matters most)

### Must have (tech)

- **Web-only gating** — No pipeline invocation for non-Web channels.
- **Widget Manifest** — Structured response: library vs generated, with stable IDs, code, and QA/a11y per widget.
- **Library-first** — Reuse pre-approved widgets; generate only gaps.
- **Selective regeneration** — Change one widget without regenerating the whole dashboard.
- **Contract-first** — Clear input/output so Maker and our service can integrate without guessing.

### Must have (non-tech)

- **Review before use** — Every new widget is previewed and explicitly approved/rejected/requested for changes.
- **Checkpoints** — Use Maker’s “Save and Deploy” after major steps so work is recoverable.
- **Pilot-ready docs** — Runbook and demo script so the next team can run and hand over.

### Success metrics (by Week 5)

| Metric | Target | For whom |
|--------|--------|----------|
| Time to first widget set | &lt; 10 minutes (standard BRD) | Product / delivery |
| Widget reuse rate | &gt; 60% (library vs total) | Design / consistency |
| QA first-pass pass rate | ≥ 80% | Engineering / quality |
| Average review iterations per widget | ≤ 1.5, trending down | All |

---

## 4. 5-week timeline (to the point)

| Week | Focus | Key outcome | Friday demo |
|------|--------|-------------|-------------|
| **1** (23–27 Feb) | KT + integration research | Contract v0 agreed; we know how Maker will call us and what we return | KT sign-off + contract v0 approved |
| **2** (2–6 Mar) | Vertical slice | Working endpoint: Web → manifest; Voice → skip. Review UI prototype | E2E demo: Web vs Voice/WhatsApp |
| **3** (9–13 Mar) | Maker hook | Maker triggers our service; review list comes from real response | Review Widgets from real service |
| **4** (16–20 Mar) | Governance + quality | Regenerate single widgets; audit log; QA/a11y gates; metrics | Iterate and regen only impacted widgets |
| **5** (23–27 Mar) | Pilot readiness | Runbook, stakeholder pack, stability, dress rehearsal | Pilot-ready + leadership narrative |

---

## 5. Who does what (RACI-style)

| Area | Person A (Agent / Service) | Person B (Maker / UX) |
|------|----------------------------|-------------------------|
| **APIs & contract** | Own: generate + regenerate endpoints, manifest schema | Input: validation, mapping to Maker |
| **Channel gating & pipeline** | Own: Web-only logic, pipeline invocation | Input: how Maker sends channel |
| **Review & governance** | Input: what’s in manifest (QA/a11y) | Own: Review Widgets UX, approve/reject/needs-changes |
| **Library & reuse** | Own: library-matching logic, stable IDs | Own: widget library mapping, version tagging |
| **Quality** | Own: QA/a11y gates, metrics, caching | Input: test scenarios, regression harness |
| **Pilot** | Input: stability, metrics summary | Own: runbook, demo script, stakeholder package |

---

## 6. Risks and mitigations (short)

| Severity | Risk | Mitigation |
|----------|------|------------|
| **High** | Unclear how Maker will call us or register widgets | Week 1 KT; contract-first service + thin adapter |
| **High** | Our widget format doesn’t match Maker’s | Mapping layer; validate with real examples in W2–W3 |
| **Medium** | Governance scope grows | Library-first; MVP governance for pilot only |
| **Medium** | Generated widgets need too many fixes | Stronger QA/a11y; regression test harness |
| **Low** | Cost or latency issues | Caching, reuse, regenerate only what changed |

---

## 7. Technical reference (for engineers)

### Architecture (one sentence each)

- **Maker Platform** — BRD, Shadow Panel, roles, dashboards, “Save and Deploy,” keyword triggers.
- **Maker Adapter** — Thin connector: channel check, context parsing, schema mapping, widget registration.
- **Widget Generation Service** — Our 4-agent pipeline (Orchestrator → Discovery → Generator → QA), 6 tools, RAG, design-system data (Metafore 31 / Untitled UI 24 / Both 55). Output: Widget Manifest + QA/a11y.

### Main endpoints (contract v0)

- **POST /maker/generate-widgets**  
  **In:** `channel`, `entryPoint`, `roles`, `pulseSections`, `designSystem` (metafore | untitledui | both), optional: `brdText`, `existingWidgets`, `widgetLibrary`, `datasourceContract`, `constraints`.  
  **Out:** `skipped` + `skipReason` when not Web; else `widgets[]` (id, name, source, code, version, qaResult, a11yResult), `metrics`, `auditLog`.

- **POST /maker/regenerate-widget**  
  **In:** `widgetId`, `priorCode`, `reviewerNotes`, `makerContext`.  
  **Out:** Updated widget with new version.

### Design systems

- **Metafore** — 31 components, purple brand (`metafore_catalog.json`, `metafore_tokens.json`).
- **Untitled UI** — 24 components, blue brand (`catalog.json`, `tokens.json`).
- **Both** — 55 merged; pipeline and RAG use the selected library.

---

## 8. Quick reference card

| Need | Where |
|------|--------|
| One-pager for leadership | Section 1 + “At a glance” table |
| Flow for product/design | Section 2 |
| Priorities and metrics | Section 3 |
| Week-by-week plan | Section 4 |
| Ownership | Section 5 |
| Risks | Section 6 |
| API and systems detail | Section 7 |
| Full visual plan | `Maker_Widget_Generation_Plan.excalidraw` |

---

*Document version: 2.0 (rectified). Aligned with 5-Week Plan docx, Maker Introduction, and PROJECT_CONTEXT.md.*
