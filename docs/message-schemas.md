# Message Schemas — API Contracts

Defines the structure of all messages exchanged between client, services, and AI layer. Designed to be **OpenAPI compatible** for future API documentation generation.

---

## 1. Chat Stream (Primary — SSE)

**Endpoint:** `POST /api/chat/stream`

### Request
```json
{
  "message": "Create a login form with email and password",
  "history": [
    {
      "role": "user",
      "content": "Show me a card component"
    },
    {
      "role": "assistant",
      "content": "Here's a card component using Tailwind CSS..."
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | The user's current prompt |
| `history` | array | No | Previous conversation messages (max 30 used) |
| `history[].role` | string | Yes | `"user"` or `"assistant"` |
| `history[].content` | string | Yes | Message text content |

### Response (SSE Stream)

Each event is a `data:` line with JSON payload:

**Chunk event** (streaming text):
```json
{ "type": "chunk", "text": "Here's a " }
```

**Done event** (stream complete):
```json
{ "type": "done" }
```

**Error event**:
```json
{ "type": "error", "error": "ANTHROPIC_API_KEY not set." }
```

---

## 2. Chat (Non-Streaming Fallback)

**Endpoint:** `POST /api/chat`

### Request
Same as `/api/chat/stream`.

### Response
```json
{
  "content": "Here's a login form component using our design system..."
}
```

**Error Response:**
```json
{
  "error": "ANTHROPIC_API_KEY not set."
}
```

---

## 3. Generate Component

**Endpoint:** `POST /api/generate`

### Request
```json
{
  "prompt": "A dashboard card showing account balance with trend indicator"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | Natural language description of the component |

### Response
```json
{
  "code": "function DashboardCard() {\n  return (\n    <div className=\"rounded-lg shadow-md p-6 bg-white\">\n      ...\n    </div>\n  );\n}\nroot.render(React.createElement(DashboardCard));"
}
```

**Error Response:**
```json
{
  "error": "anthropic not installed. pip install anthropic"
}
```

---

## 4. Generate Variants

**Endpoint:** `POST /api/generate-variants`

### Request
```json
{
  "prompt": "A user profile card",
  "count": 3,
  "keywords": ["Minimal", "Bold", "Playful"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | Component description |
| `count` | number | No | Number of variants (2 or 3, default 2) |
| `keywords` | array | No | Style keywords for each variant |

### Response
```json
{
  "variants": [
    {
      "code": "function CardMinimal() { ... }",
      "keywords": "Minimal"
    },
    {
      "code": "function CardBold() { ... }",
      "keywords": "Bold"
    },
    {
      "code": "function CardPlayful() { ... }",
      "keywords": "Playful"
    }
  ]
}
```

---

## 5. Preview

**Endpoint:** `POST /api/preview`

### Request
```json
{
  "code": "function LoginForm() {\n  return <div>...</div>;\n}\nroot.render(React.createElement(LoginForm));"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | string | Yes | React/JSX code to render |

### Response
- **Content-Type:** `text/html`
- Returns a complete HTML document with React 18 + Babel + Tailwind CDN that renders the code in a sandboxed iframe

---

## 6. Health Check

**Endpoint:** `GET /api/health`

### Response
```json
{
  "ok": true,
  "has_api_key": true
}
```

---

## 7. Design System Catalog

**Endpoint:** `GET /api/catalog`

### Response
```json
{
  "tokens": {
    "colors": { "primary": { "500": "#0ea5e9" } },
    "typography": { "fontFamily": { "sans": "ui-sans-serif, system-ui" } },
    "spacing": { "4": "1rem" },
    "radius": { "md": "0.375rem" }
  },
  "catalog": {
    "components": [
      {
        "name": "Button",
        "import": "import { Button } from '@/components/base/buttons/button'",
        "description": "Primary, secondary, outline, ghost variants.",
        "props": ["children", "variant?", "size?", "disabled?", "onPress?"]
      }
    ]
  }
}
```

---

## Future Messages (Proposed)

### Store Conversation (Service → Database)
```json
{
  "conversationId": "conv_abc123",
  "userId": "user_001",
  "messages": [...],
  "metadata": {
    "createdAt": "2026-02-13T10:00:00Z",
    "updatedAt": "2026-02-13T10:05:00Z",
    "messageCount": 12
  }
}
```

### Load LTM Context (Service → Memory Store)
```json
{
  "userId": "user_001",
  "query": "login form",
  "limit": 5
}
```

### LTM Response
```json
{
  "relevantHistory": [
    {
      "conversationId": "conv_older",
      "summary": "Generated a login form with email/password and OAuth buttons",
      "timestamp": "2026-02-10T14:30:00Z"
    }
  ]
}
```
