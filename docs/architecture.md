# Architecture — Milestone 1 Design System Agent

## Overview

A ChatGPT-style AI agent that generates React UI components from natural language prompts using a local design system (catalog + tokens) and the Claude API. The system is designed as a microservice with a clear separation of concerns across layers.

---

## Current Architecture

```
┌────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                        │
│                                                        │
│   Chatbot UI (Port 3851)    Dashboard UI (Port 3850)   │
│   React/JSX + SSE           React/JSX + REST           │
└──────────────┬─────────────────────┬───────────────────┘
               │                     │
┌──────────────▼─────────────────────▼───────────────────┐
│                  TRANSPORT LAYER                       │
│              HTTP REST + SSE Streaming                  │
└──────────────┬─────────────────────────────────────────┘
               │
┌──────────────▼─────────────────────────────────────────┐
│                API / SERVICE LAYER                     │
│                                                        │
│   Chat Service          Generate Service    Preview    │
│   /api/chat             /api/generate       /api/      │
│   /api/chat/stream      /api/generate-      preview    │
│   (SSE)                 variants                       │
└──────────────┬─────────────────────────────────────────┘
               │
┌──────────────▼─────────────────────────────────────────┐
│                   AI / LLM LAYER                       │
│                                                        │
│   Claude API (claude-sonnet-4-20250514)                        │
│   via Anthropic SDK                                    │
│   System Prompt = PROJECT_CONTEXT + Tokens + Catalog   │
└──────────────┬─────────────────────────────────────────┘
               │
┌──────────────▼─────────────────────────────────────────┐
│                    DATA LAYER                          │
│                                                        │
│   catalog.json     tokens.json     localStorage        │
│   (components)     (design tokens) (chat history,      │
│                                     client-side)       │
└────────────────────────────────────────────────────────┘
```

### Current Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| Client | React 18 (UMD/CDN), Babel standalone | No build step required |
| Transport | HTTP REST + SSE | Server-Sent Events for streaming chat |
| Backend | Python 3, `http.server` + `ThreadingMixIn` | Multi-threaded for concurrent requests |
| AI | Anthropic Claude API | Streaming SSE for real-time chat responses |
| Data | JSON files + localStorage | No database, no server-side persistence |

---

## Proposed Architecture (Future State)

### What Changes

| Component | Current | Proposed |
|-----------|---------|----------|
| Transport | HTTP + SSE only | Add **gRPC** for inter-service calls, **Kafka** for async events |
| Database | None (JSON files + localStorage) | **PostgreSQL** with **Alembic** migrations |
| Memory | localStorage (client-side only) | **STM** (session context) + **LTM** (persisted in DB) |
| Guidelines | Hardcoded in system prompt | Loaded from `coding_guidelines.md` file |
| Messages | Ad-hoc JSON payloads | **Structured schemas** (OpenAPI compatible) |

### Transport Layer Decision

| Option | Strengths | Use Case |
|--------|----------|----------|
| **HTTP REST + SSE** | Simple, already working, browser-native | Client ↔ Server communication (keep this) |
| **gRPC** | Typed contracts, high performance, bi-directional streaming | Inter-service communication (future microservices) |
| **Kafka** | Async, decoupled, event replay, fan-out | Event-driven workflows (code generated → store + notify) |

**Recommendation:** Keep HTTP + SSE for client-facing API. Add Kafka later when multiple microservices need to react to the same events (e.g., "code generated" event triggers storage, analytics, and notification).

### Database Design

The microservice should own its database (PostgreSQL):

| Table | Purpose |
|-------|---------|
| `conversations` | Store chat sessions with messages (replaces localStorage) |
| `generated_code` | Archive all generated code with metadata |
| `user_preferences` | User settings and customization |
| `coding_guidelines` | Version-controlled guidelines (optional, can stay as file) |

Schema migrations managed by **Alembic** — version-controlled, reversible changes.

### Memory Architecture (STM / LTM)

| Type | Scope | Storage | Purpose |
|------|-------|---------|---------|
| **STM** (Short-Term Memory) | Current session | In-memory / Redis | Active conversation context, recent messages (already exists as `history[]` array) |
| **LTM** (Long-Term Memory) | Cross-session | PostgreSQL | Past conversations, user preferences, frequently used patterns, learning from feedback |

**Flow:**
1. User sends message → STM provides recent context
2. LTM queried for relevant past interactions
3. Both injected into Claude system prompt
4. Response stored in both STM (session) and LTM (persistent)

---

## Key API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/health` | Health check + API key status |
| GET | `/api/catalog` | Design system tokens + components |
| POST | `/api/chat/stream` | Streaming chat via SSE |
| POST | `/api/chat` | Non-streaming chat (fallback) |
| POST | `/api/preview` | Render code in sandboxed HTML |
| POST | `/api/generate` | Generate single component |
| POST | `/api/generate-variants` | Generate 2-3 style variants |

---

## Deployment

| Environment | Method |
|------------|--------|
| Local | `cd chatbot && python server.py` → http://localhost:3851 |
| GitHub Codespaces | Auto-configured via `.devcontainer/devcontainer.json` |
| Docker | `docker-compose up` (MCP server) |
| **Ctrlagent Maker** | **Future** — Deploy as an App + Agent on the Metafore AI platform |

---

## Future: Ctrlagent Maker Platform Deployment

### What is Maker?

Maker (v0.9) is an **agentic app generation co-pilot** on the Ctrlagent platform. It allows you to create Apps, Agents, Tools, and Dashboards — either from scratch or from a BRD (Business Requirements Document).

### Key Maker Concepts

| Concept | What It Is | Maps To (Our System) |
|---------|-----------|---------------------|
| **App** | Container for agents and dashboards | The "Design System Agent" application |
| **Agent** | AI agent with purpose, responsibilities, policies | Our Chatbot — generates UI from prompts |
| **Integration** | Connection to an external API (base URL + auth) | Our Python backend server endpoints |
| **Endpoint** | Specific API route within an Integration | `/api/chat/stream`, `/api/generate`, `/api/preview`, etc. |
| **Tool** | Agent capability created from an Endpoint | Each API action the agent can perform |
| **Pulse** | Role-based dashboard | Dashboard UI (port 3850) — evolves into a Pulse dashboard |
| **System of Record (SoR)** | Where data lives | External SoR — our PostgreSQL database (or Supabase) |

### Maker 0.9 Architecture (Decoupled)

In Maker 0.9, the **System of Record and APIs are created externally** and then connected to agents through Integrations → Endpoints → Tools:

```
┌─────────────────────────────────────────────────────┐
│              CTRLAGENT MAKER PLATFORM                │
│                                                     │
│   ┌──────────────┐    ┌──────────────────────────┐  │
│   │  Banking App  │    │  Design System Agent App │  │
│   └──────┬───────┘    └──────────┬───────────────┘  │
│          │                       │                  │
│   ┌──────▼───────────────────────▼───────────────┐  │
│   │              AGENTS                          │  │
│   │  Retail Banking Agent | UI Generation Agent  │  │
│   └──────────────────┬───────────────────────────┘  │
│                      │                              │
│   ┌──────────────────▼───────────────────────────┐  │
│   │              TOOLS                           │  │
│   │  (Created from Integrations + Endpoints)     │  │
│   │  ChatWithAgent | GenerateUI | PreviewCode    │  │
│   │  GenerateVariants | GetCatalog               │  │
│   └──────────────────┬───────────────────────────┘  │
│                      │                              │
│   ┌──────────────────▼───────────────────────────┐  │
│   │          PULSE DASHBOARDS                    │  │
│   │  Role-based views (Developer, Designer, PM)  │  │
│   └──────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │
          Integrations (HTTP/REST)
                       │
┌──────────────────────▼──────────────────────────────┐
│           EXTERNAL SYSTEM OF RECORD                 │
│                                                     │
│   PostgreSQL / Supabase                             │
│   Tables: conversations, messages, generated_code   │
│   APIs tested in Postman → cURL → Maker Tools      │
└─────────────────────────────────────────────────────┘
```

### How Our System Maps to Maker

#### Step 1: Set Up External SoR (Supabase / PostgreSQL)

Create the database tables externally (see `docs/database-plan.md`):
- `conversations`, `messages`, `generated_code`, `user_preferences`
- Expose REST APIs via Supabase (auto-generated CRUD)
- Test APIs in Postman, export as cURL commands

#### Step 2: Create the App + Agent in Maker

Prompt Maker:
> "Create a Design System Agent app with a UI Generation agent. The agent generates React UI components from natural language prompts using a design system catalog and the Claude API. It supports streaming chat, code generation, multi-variant generation, and live preview."

#### Step 3: Create Integrations + Tools

For each API endpoint, provide tested cURL to Maker:

| Tool Name | Endpoint | cURL Source |
|-----------|----------|-------------|
| `ChatWithAgent` | `POST /api/chat/stream` | Streaming chat with conversation context |
| `GenerateComponent` | `POST /api/generate` | Generate a single React component |
| `GenerateVariants` | `POST /api/generate-variants` | Generate 2-3 style variants |
| `PreviewCode` | `POST /api/preview` | Render code in sandboxed iframe |
| `GetDesignCatalog` | `GET /api/catalog` | Fetch design tokens + components |
| `HealthCheck` | `GET /api/health` | Verify API key and server status |

**Recommended approach:** Use Maker's **one-step cURL method** — paste the tested cURL and Maker auto-creates Integration → Endpoint → Tool.

#### Step 4: Deploy and Create Pulse Dashboards

1. Type `Deploy` in Maker to publish
2. Create role-based Pulse dashboards:

| Role | Dashboard Content |
|------|------------------|
| **Developer** | Generated code history, component catalog, variant comparison |
| **Designer** | Live previews, style variants, design token reference |
| **Project Manager** | Usage analytics, component generation counts, conversation summaries |

#### Step 5: Iterate

Maker auto-saves changes. Deploy after every meaningful update:
- After app + agent creation
- After tool/integration creation
- After dashboard creation

### BRD Template for Maker Submission

When ready to deploy to Maker, prepare a BRD with:

1. **Executive Summary** — Design System Agent for UI generation
2. **Users & Roles** — Developer, Designer, PM
3. **Entities** — Internal SoR if needed (or external via Supabase)
4. **Integrations** — Our backend API endpoints with cURL commands
5. **Agent Definition** — Purpose, responsibilities, tools, guardrails
6. **User Journeys** — "Generate a login form", "Compare 3 variants", etc.
7. **Dashboards** — Pulse configs per role
