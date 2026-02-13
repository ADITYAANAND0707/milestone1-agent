# Database Plan — PostgreSQL + Alembic

## Overview

Migrate from client-side localStorage and static JSON files to a server-side PostgreSQL database with Alembic-managed schema migrations. This enables persistent storage, cross-session memory (STM/LTM), and multi-user support.

---

## Current State (No Database)

| Data | Storage | Limitation |
|------|---------|-----------|
| Chat history | `localStorage` (browser) | Lost on clear, not shareable, single device |
| Design system | `catalog.json` + `tokens.json` | Static files, no versioning |
| Generated code | Not persisted server-side | Lost after session ends |
| User preferences | None | No personalization |

---

## Proposed Schema

### Table: `conversations`

Stores chat sessions, replacing `localStorage`.

```sql
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(255),
    title           VARCHAR(500),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_count   INTEGER DEFAULT 0,
    is_archived     BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_updated ON conversations(updated_at DESC);
```

### Table: `messages`

Individual messages within a conversation.

```sql
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,
    code            TEXT,
    variant_codes   JSONB,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
```

### Table: `generated_code`

Archive of all generated components for reuse and analytics.

```sql
CREATE TABLE generated_code (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    message_id      UUID REFERENCES messages(id) ON DELETE SET NULL,
    component_name  VARCHAR(255),
    code            TEXT NOT NULL,
    prompt          TEXT,
    variant_label   VARCHAR(255),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_generated_code_name ON generated_code(component_name);
CREATE INDEX idx_generated_code_created ON generated_code(created_at DESC);
```

### Table: `user_preferences`

User settings and customization.

```sql
CREATE TABLE user_preferences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(255) UNIQUE NOT NULL,
    preferred_style VARCHAR(50) DEFAULT 'minimal',
    dark_mode       BOOLEAN DEFAULT TRUE,
    settings        JSONB DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Table: `memory_long_term` (LTM)

Long-term memory for cross-session context.

```sql
CREATE TABLE memory_long_term (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(255) NOT NULL,
    memory_type     VARCHAR(50) NOT NULL CHECK (memory_type IN ('pattern', 'preference', 'correction', 'summary')),
    content         TEXT NOT NULL,
    embedding       VECTOR(1536),
    relevance_score FLOAT DEFAULT 1.0,
    source_conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ltm_user ON memory_long_term(user_id, memory_type);
CREATE INDEX idx_ltm_accessed ON memory_long_term(last_accessed DESC);
```

---

## Alembic Migration Plan

### Setup

```bash
pip install alembic psycopg2-binary sqlalchemy
alembic init alembic
```

### Migration Sequence

| Version | Migration | Description |
|---------|-----------|-------------|
| `001` | `create_conversations` | Create conversations table |
| `002` | `create_messages` | Create messages table with FK to conversations |
| `003` | `create_generated_code` | Create generated_code archive table |
| `004` | `create_user_preferences` | Create user preferences table |
| `005` | `create_memory_ltm` | Create long-term memory table |
| `006` | `add_indexes` | Add performance indexes |

### Running Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "create_conversations"

# Apply all migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Check current version
alembic current
```

---

## STM vs LTM Implementation

### STM (Short-Term Memory)

- **Scope:** Current conversation session
- **Storage:** In-memory (Python dict) or Redis
- **Content:** Last 30 messages from the `history[]` array
- **Lifetime:** Cleared when conversation ends or session times out
- **Already exists:** The `history` parameter in `/api/chat/stream` serves as STM

### LTM (Long-Term Memory)

- **Scope:** Across all sessions for a user
- **Storage:** PostgreSQL `memory_long_term` table
- **Content types:**
  - `pattern` — Commonly requested UI patterns ("user always asks for dark mode cards")
  - `preference` — Learned style preferences ("user prefers minimal design")
  - `correction` — User corrections to remember ("don't use inline styles")
  - `summary` — Conversation summaries for context retrieval
- **Retrieval:** Query by user_id + semantic similarity (using embeddings) or keyword match
- **Injection:** Top 3-5 relevant LTM entries added to Claude system prompt

### Memory Flow

```
User sends message
       │
       ▼
┌─────────────┐     ┌─────────────┐
│ STM: Recent │     │ LTM: Query  │
│ 30 messages │     │ relevant    │
│ (in-memory) │     │ memories    │
└──────┬──────┘     └──────┬──────┘
       │                   │
       ▼                   ▼
┌──────────────────────────────────┐
│     Build System Prompt          │
│  = Context + Tokens + Catalog    │
│  + Guidelines + STM + LTM       │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│         Claude API Call          │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Store response in STM + LTM    │
│  Return to client via SSE       │
└──────────────────────────────────┘
```

---

## Environment Variables (New)

```env
# Add to .env alongside ANTHROPIC_API_KEY
DATABASE_URL=postgresql://user:password@localhost:5432/milestone1_agent
REDIS_URL=redis://localhost:6379/0
```

---

## Migration Path (Incremental)

1. **Phase 1 (Now):** Keep localStorage, add coding guidelines to system prompt
2. **Phase 2:** Add PostgreSQL for conversation persistence (replace localStorage)
3. **Phase 3:** Add generated_code archival and user_preferences
4. **Phase 4:** Add LTM with semantic search (requires embeddings)
5. **Phase 5:** Add Redis for STM caching and session management
6. **Phase 6:** Deploy to Ctrlagent Maker platform as External SoR (see below)

---

## Ctrlagent Maker Platform — External SoR Integration

### Maker 0.9 Architecture (Decoupled)

In Maker 0.9, the **System of Record (SoR) is created externally** and connected to agents through Integrations → Endpoints → Tools. Our database serves as the External SoR.

### Recommended: Supabase as SoR

Supabase is the recommended approach because it:
- Runs on PostgreSQL (same schema we've designed above)
- Auto-exposes REST APIs for all tables (no extra backend needed)
- Provides API Key + Base URL ready for Maker integration
- Works with Maker's cURL-based tool creation

### Setup Steps

1. **Create Supabase project** (company or free account)
2. **Create tables** using the DDL from the schema above (conversations, messages, generated_code, etc.)
3. **Seed sample data** using the SQL Editor
4. **Test APIs in Postman** — Supabase auto-generates CRUD endpoints:
   - `GET /rest/v1/conversations?select=*` — list conversations
   - `POST /rest/v1/messages` — create message
   - `GET /rest/v1/generated_code?select=*&conversation_id=eq.{id}` — get code by conversation
5. **Export as cURL** — each tested API becomes a Maker tool

### Mapping Tables to Maker Tools

| Supabase Table | Maker Tool Name | API Method | Purpose |
|----------------|----------------|------------|---------|
| `conversations` | `ListConversations` | `GET /rest/v1/conversations` | Fetch user's chat sessions |
| `conversations` | `CreateConversation` | `POST /rest/v1/conversations` | Start new chat session |
| `messages` | `GetMessages` | `GET /rest/v1/messages?conversation_id=eq.{id}` | Load chat history |
| `messages` | `SaveMessage` | `POST /rest/v1/messages` | Store message |
| `generated_code` | `GetGeneratedCode` | `GET /rest/v1/generated_code` | Browse code archive |
| `generated_code` | `SaveGeneratedCode` | `POST /rest/v1/generated_code` | Archive generated component |
| `user_preferences` | `GetPreferences` | `GET /rest/v1/user_preferences?user_id=eq.{id}` | Load user settings |

### Maker Integration Example

In Maker compose bar:
```
"Create a tool using this cURL"
```

Then paste:
```bash
curl --location 'https://your-project.supabase.co/rest/v1/conversations?select=*' \
--header 'apikey: your_supabase_api_key' \
--header 'Authorization: Bearer your_supabase_api_key'
```

Maker will automatically:
1. Create an **Integration** (Supabase connection)
2. Create an **Endpoint** (the API route)
3. Create a **Tool** (ListConversations) and attach it to the agent

### Environment Variables for Supabase

```env
# Add to .env for Supabase SoR
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_API_KEY=your_supabase_api_key
```
