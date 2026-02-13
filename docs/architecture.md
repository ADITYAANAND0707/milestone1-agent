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
