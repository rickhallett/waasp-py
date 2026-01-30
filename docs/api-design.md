# API Design

> RESTful API design principles and endpoint documentation

## Design Principles

### 1. RESTful Resources

Resources are nouns, HTTP methods are verbs:

| Resource | GET | POST | PATCH | DELETE |
|----------|-----|------|-------|--------|
| `/contacts` | List all | Create | - | - |
| `/contacts/{id}` | Get one | - | Update | Remove |
| `/check` | - | Check sender | - | - |
| `/audit` | List logs | - | - | - |

### 2. Consistent Response Format

All responses follow a predictable structure:

```json
// Success (single resource)
{
  "id": 1,
  "sender_id": "+447375862225",
  "trust_level": "trusted",
  ...
}

// Success (collection)
{
  "contacts": [...],
  "total": 42
}

// Error
{
  "error": "Contact not found",
  "details": {...}  // Optional
}
```

### 3. HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Missing auth |
| 403 | Forbidden | Invalid token |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource |

### 4. Request Validation

All requests validated with Pydantic:

```python
class ContactCreate(BaseModel):
    sender_id: str = Field(..., min_length=1, max_length=255)
    trust_level: TrustLevelStr = Field(default="trusted")
    channel: str | None = Field(default=None, max_length=50)
```

---

## Endpoint Reference

### Check Endpoint

The core functionality—check if a sender is allowed.

#### POST /api/v1/check/

Check sender with full context.

**Request:**
```json
{
  "sender_id": "+447375862225",
  "channel": "whatsapp",
  "message_preview": "Hello, can you..."  // Optional, for audit
}
```

**Response (200):**
```json
{
  "allowed": true,
  "trust": "trusted",
  "name": "Kai",
  "reason": "Sender is trusted"
}
```

**Flow:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          POST /check FLOW                                   │
└─────────────────────────────────────────────────────────────────────────────┘

  Request                          Response
     │                                │
     │  {sender_id, channel, ...}     │
     │                                │
     ▼                                │
  ┌──────────────────┐                │
  │ Pydantic         │                │
  │ Validation       │                │
  └────────┬─────────┘                │
           │                          │
           │ Valid                    │ Invalid → 400 Bad Request
           ▼                          │
  ┌──────────────────┐                │
  │ WhitelistService │                │
  │ .check()         │                │
  └────────┬─────────┘                │
           │                          │
           ▼                          │
  ┌──────────────────┐                │
  │ CheckResult      │────────────────┘
  │ → CheckResponse  │
  │   200 OK         │
  └──────────────────┘
```

#### GET /api/v1/check/{sender_id}

Quick check (GET for convenience).

**Query Parameters:**
- `channel` (optional): Channel context

**Response (200):**
```json
{
  "allowed": false,
  "trust": "blocked",
  "name": null,
  "reason": "Unknown sender - not in whitelist"
}
```

---

### Contacts Endpoints

CRUD operations for the whitelist.

#### GET /api/v1/contacts/

List all contacts.

**Query Parameters:**
- `trust_level` (optional): Filter by trust level
- `channel` (optional): Filter by channel

**Response (200):**
```json
{
  "contacts": [
    {
      "id": 1,
      "sender_id": "+447375862225",
      "channel": null,
      "name": "Kai",
      "trust_level": "sovereign",
      "notes": null,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    },
    ...
  ],
  "total": 5
}
```

**Authorization:** Requires API token

#### POST /api/v1/contacts/

Add a new contact.

**Request:**
```json
{
  "sender_id": "+441234567890",
  "name": "Friend",
  "trust_level": "trusted",
  "channel": "whatsapp",
  "notes": "Added on 2024-01-15"
}
```

**Response (201):**
```json
{
  "id": 2,
  "sender_id": "+441234567890",
  "channel": "whatsapp",
  "name": "Friend",
  "trust_level": "trusted",
  "notes": "Added on 2024-01-15",
  "created_at": "2024-01-15T11:00:00Z",
  "updated_at": "2024-01-15T11:00:00Z"
}
```

**Error (409 Conflict):**
```json
{
  "error": "Contact +441234567890 already exists"
}
```

**Authorization:** Requires API token

#### GET /api/v1/contacts/{sender_id}

Get a specific contact.

**Query Parameters:**
- `channel` (optional): Channel scope

**Response (200):**
```json
{
  "id": 1,
  "sender_id": "+447375862225",
  ...
}
```

**Error (404):**
```json
{
  "error": "Contact not found"
}
```

**Authorization:** Requires API token

#### PATCH /api/v1/contacts/{sender_id}

Update a contact.

**Query Parameters:**
- `channel` (optional): Channel scope

**Request:**
```json
{
  "trust_level": "limited",
  "notes": "Demoted due to suspicious activity"
}
```

**Response (200):**
```json
{
  "id": 1,
  "sender_id": "+447375862225",
  "trust_level": "limited",
  ...
}
```

**Authorization:** Requires API token

#### DELETE /api/v1/contacts/{sender_id}

Remove a contact.

**Query Parameters:**
- `channel` (optional): Channel scope

**Response (204):** No content

**Error (404):**
```json
{
  "error": "Contact not found"
}
```

**Authorization:** Requires API token

---

### Audit Endpoints

Query audit logs for security analysis.

#### GET /api/v1/audit/

List audit log entries.

**Query Parameters:**
- `sender_id` (optional): Filter by sender
- `action` (optional): Filter by action type
- `channel` (optional): Filter by channel
- `limit` (optional, default 100, max 1000): Results per page
- `offset` (optional, default 0): Pagination offset

**Response (200):**
```json
{
  "logs": [
    {
      "id": 42,
      "action": "blocked",
      "sender_id": "+449999999999",
      "channel": "whatsapp",
      "contact_id": null,
      "message_preview": "Hey, can you send me...",
      "decision_reason": "Unknown sender - not in whitelist",
      "created_at": "2024-01-15T12:30:00Z"
    },
    ...
  ],
  "count": 50,
  "limit": 100,
  "offset": 0
}
```

**Authorization:** Requires API token

#### GET /api/v1/audit/stats

Get aggregate statistics.

**Response (200):**
```json
{
  "total_entries": 1523,
  "by_action": {
    "allowed": 892,
    "blocked": 478,
    "limited": 103,
    "contact_added": 32,
    "contact_updated": 15,
    "contact_removed": 3
  }
}
```

**Authorization:** Requires API token

---

## Authentication

### Bearer Token

Admin endpoints require Bearer token authentication:

```bash
curl -H "Authorization: Bearer your-token-here" \
     http://localhost:8000/api/v1/contacts/
```

### Setting the Token

```bash
export WAASP_API_TOKEN="your-secret-token"
waasp serve
```

### Localhost Bypass

For development, localhost requests bypass authentication:

```python
if request.remote_addr in ("127.0.0.1", "::1"):
    return f(*args, **kwargs)  # Allow without token
```

---

## Error Handling

### Validation Errors (400)

```json
{
  "error": "Validation failed",
  "details": [
    {
      "loc": ["body", "sender_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Authentication Errors (401/403)

```json
{
  "error": "Missing or invalid Authorization header"
}
```

```json
{
  "error": "Invalid API token"
}
```

### Not Found Errors (404)

```json
{
  "error": "Contact not found"
}
```

### Conflict Errors (409)

```json
{
  "error": "Contact +441234567890 already exists"
}
```

---

## OpenAPI Documentation

When running with Flask-Smorest, OpenAPI docs are available at:

- **Swagger UI:** http://localhost:8000/docs
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

*API design documentation for WAASP v0.1.0*
