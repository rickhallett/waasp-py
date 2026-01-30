# WAASP Architecture

> A deep dive into the system design decisions behind WAASP

## Table of Contents

- [Overview](#overview)
- [Design Principles](#design-principles)
- [System Architecture](#system-architecture)
- [Component Breakdown](#component-breakdown)
- [Data Flow](#data-flow)
- [Scalability Considerations](#scalability-considerations)
- [Further Reading](#further-reading)

---

## Overview

WAASP (Whitelist for Agentic AI Security Protocol) is a security layer that sits between untrusted message sources and AI agents. Its primary function is simple: **decide whether a message should reach the agent**.

```
                    ┌─────────────────────────────────────┐
                    │         UNTRUSTED WORLD             │
                    │  (WhatsApp, Telegram, Email, etc.)  │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │              WAASP                  │
                    │     "Should this message pass?"     │
                    └──────────────────┬──────────────────┘
                                       │
                         ┌─────────────┴─────────────┐
                         │                           │
                         ▼                           ▼
                    ┌─────────┐                 ┌─────────┐
                    │  ALLOW  │                 │  BLOCK  │
                    │    ↓    │                 │    ↓    │
                    │  Agent  │                 │   Log   │
                    └─────────┘                 └─────────┘
```

## Design Principles

### 1. Fail Closed

Unknown senders are **blocked by default**. This is a security-first stance that prioritizes protection over convenience.

```python
# Default trust level for unknown senders
DEFAULT_TRUST_LEVEL = TrustLevel.BLOCKED
```

### 2. Explicit Trust

Trust is never inferred. Every allowed sender must be explicitly added to the whitelist with a defined trust level.

### 3. Audit Everything

Every decision—allow or block—is logged. This creates an audit trail for:
- Security analysis
- Debugging
- Compliance
- Pattern detection

### 4. Channel Awareness

The same sender may have different trust levels on different channels. A contact trusted on WhatsApp may be blocked on email.

### 5. Defense in Depth

WAASP is one layer in a security stack, not a complete solution. It complements:
- Platform-level authentication (WhatsApp verifies phone numbers)
- Agent-level guardrails
- Rate limiting
- Anomaly detection

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WAASP SYSTEM                                   │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                           API LAYER                                   │  │
│  │                                                                       │  │
│  │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                │  │
│  │   │   /check    │   │  /contacts  │   │   /audit    │                │  │
│  │   │             │   │             │   │             │                │  │
│  │   │  Whitelist  │   │   CRUD      │   │   Query     │                │  │
│  │   │  Decisions  │   │   Mgmt      │   │   Logs      │                │  │
│  │   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘                │  │
│  │          │                 │                 │                        │  │
│  └──────────┼─────────────────┼─────────────────┼────────────────────────┘  │
│             │                 │                 │                            │
│  ┌──────────┴─────────────────┴─────────────────┴────────────────────────┐  │
│  │                        SERVICE LAYER                                  │  │
│  │                                                                       │  │
│  │   ┌─────────────────────────┐   ┌─────────────────────────┐          │  │
│  │   │    WhitelistService     │   │     AuditService        │          │  │
│  │   │                         │   │                         │          │  │
│  │   │  • check()              │   │  • log_check()          │          │  │
│  │   │  • add_contact()        │   │  • log_admin_action()   │          │  │
│  │   │  • update_contact()     │   │  • get_logs()           │          │  │
│  │   │  • remove_contact()     │   │  • get_stats()          │          │  │
│  │   │  • list_contacts()      │   │                         │          │  │
│  │   └───────────┬─────────────┘   └───────────┬─────────────┘          │  │
│  │               │                             │                         │  │
│  └───────────────┼─────────────────────────────┼─────────────────────────┘  │
│                  │                             │                            │
│  ┌───────────────┴─────────────────────────────┴─────────────────────────┐  │
│  │                         DATA LAYER                                    │  │
│  │                                                                       │  │
│  │   ┌─────────────────────────┐   ┌─────────────────────────┐          │  │
│  │   │       Contact           │   │       AuditLog          │          │  │
│  │   │                         │   │                         │          │  │
│  │   │  • sender_id (indexed)  │   │  • action               │          │  │
│  │   │  • channel              │   │  • sender_id (indexed)  │          │  │
│  │   │  • trust_level          │   │  • timestamp            │          │  │
│  │   │  • name                 │   │  • decision_reason      │          │  │
│  │   └─────────────────────────┘   └─────────────────────────┘          │  │
│  │                                                                       │  │
│  │                    ┌─────────────────────┐                            │  │
│  │                    │  PostgreSQL/SQLite  │                            │  │
│  │                    └─────────────────────┘                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        ASYNC LAYER                                    │  │
│  │                                                                       │  │
│  │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                │  │
│  │   │   Celery    │   │    Redis    │   │   Tasks     │                │  │
│  │   │   Worker    │◄──┤   Broker    │◄──┤             │                │  │
│  │   │             │   │             │   │ • notify    │                │  │
│  │   │             │   │             │   │ • aggregate │                │  │
│  │   │             │   │             │   │ • cleanup   │                │  │
│  │   └─────────────┘   └─────────────┘   └─────────────┘                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### API Layer

The API layer handles HTTP requests and response formatting. Built with:

- **Flask**: Lightweight WSGI framework
- **Flask-Smorest**: OpenAPI 3.0 documentation generation
- **Pydantic**: Request/response validation with type hints

See: [docs/api-design.md](docs/api-design.md)

### Service Layer

Business logic is encapsulated in service classes, keeping it:
- Testable (services can be unit tested without HTTP)
- Reusable (CLI and API use the same services)
- Clean (API handlers are thin)

See: [docs/service-layer.md](docs/service-layer.md)

### Data Layer

SQLAlchemy 2.0 models with:
- Type hints via `Mapped[]`
- Alembic migrations
- Proper indexing for query performance

See: [docs/data-model.md](docs/data-model.md)

### Async Layer

Celery handles background tasks:
- Notifications when senders are blocked
- Audit log aggregation
- Periodic cleanup of old logs

See: [docs/async-architecture.md](docs/async-architecture.md)

---

## Data Flow

### Check Request Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         CHECK REQUEST FLOW                                 │
└────────────────────────────────────────────────────────────────────────────┘

  Client                API              WhitelistService           Database
    │                    │                      │                      │
    │  POST /check       │                      │                      │
    │  {sender_id}       │                      │                      │
    │───────────────────►│                      │                      │
    │                    │                      │                      │
    │                    │  check(sender_id)    │                      │
    │                    │─────────────────────►│                      │
    │                    │                      │                      │
    │                    │                      │  SELECT contact      │
    │                    │                      │  WHERE sender_id=?   │
    │                    │                      │─────────────────────►│
    │                    │                      │                      │
    │                    │                      │◄─────────────────────│
    │                    │                      │  Contact | None      │
    │                    │                      │                      │
    │                    │                      │                      │
    │                    │                      ├──────────────────────┤
    │                    │                      │ DECISION LOGIC       │
    │                    │                      │                      │
    │                    │                      │ if no contact:       │
    │                    │                      │   → BLOCKED          │
    │                    │                      │ elif blocked:        │
    │                    │                      │   → BLOCKED          │
    │                    │                      │ elif limited:        │
    │                    │                      │   → LIMITED (allow)  │
    │                    │                      │ else:                │
    │                    │                      │   → ALLOWED          │
    │                    │                      ├──────────────────────┤
    │                    │                      │                      │
    │                    │                      │  INSERT audit_log    │
    │                    │                      │─────────────────────►│
    │                    │                      │                      │
    │                    │  CheckResult         │                      │
    │                    │◄─────────────────────│                      │
    │                    │                      │                      │
    │  {allowed, trust}  │                      │                      │
    │◄───────────────────│                      │                      │
    │                    │                      │                      │
```

### Channel-Specific Lookup

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    CHANNEL-SPECIFIC LOOKUP PRIORITY                        │
└────────────────────────────────────────────────────────────────────────────┘

  Given: sender_id="+447375862225", channel="telegram"

  Step 1: Look for channel-specific match
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  SELECT * FROM contacts                                                 │
  │  WHERE sender_id = '+447375862225'                                      │
  │    AND channel = 'telegram'                                             │
  └─────────────────────────────────────────────────────────────────────────┘
        │
        ├── Found? → Use this contact
        │
        └── Not found? → Continue to Step 2

  Step 2: Fall back to global match
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  SELECT * FROM contacts                                                 │
  │  WHERE sender_id = '+447375862225'                                      │
  │    AND channel IS NULL                                                  │
  └─────────────────────────────────────────────────────────────────────────┘
        │
        ├── Found? → Use this contact
        │
        └── Not found? → Return None (sender will be blocked)
```

---

## Scalability Considerations

### Current Design (Single Instance)

Suitable for:
- Single user / small team
- < 10K checks/day
- Single region deployment

### Horizontal Scaling

For higher throughput:

```
                         ┌──────────────────┐
                         │   Load Balancer  │
                         └────────┬─────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
            ▼                     ▼                     ▼
      ┌──────────┐          ┌──────────┐          ┌──────────┐
      │  Web 1   │          │  Web 2   │          │  Web 3   │
      └────┬─────┘          └────┬─────┘          └────┬─────┘
           │                     │                     │
           └──────────────┬──────┴──────────────┬──────┘
                          │                     │
                          ▼                     ▼
                    ┌──────────┐          ┌──────────┐
                    │ Postgres │          │  Redis   │
                    │ (Primary)│          │ Cluster  │
                    └────┬─────┘          └──────────┘
                         │
                    ┌────┴────┐
                    ▼         ▼
              ┌──────────┐ ┌──────────┐
              │ Replica  │ │ Replica  │
              └──────────┘ └──────────┘
```

### Caching Strategy

For read-heavy workloads, add Redis caching:

```python
# Pseudo-code for cached check
def check(sender_id: str, channel: str | None) -> CheckResult:
    cache_key = f"contact:{sender_id}:{channel or 'global'}"
    
    # Try cache first
    cached = redis.get(cache_key)
    if cached:
        return CheckResult.from_cache(cached)
    
    # Fall back to database
    contact = db.query(Contact).filter(...).first()
    
    # Cache for 5 minutes
    redis.setex(cache_key, 300, contact.to_cache())
    
    return CheckResult(...)
```

---

## Further Reading

| Document | Description |
|----------|-------------|
| [docs/data-model.md](docs/data-model.md) | Database schema and relationships |
| [docs/api-design.md](docs/api-design.md) | API design principles and endpoints |
| [docs/security-model.md](docs/security-model.md) | Trust levels and threat model |
| [docs/async-architecture.md](docs/async-architecture.md) | Celery and event-driven design |
| [docs/deployment.md](docs/deployment.md) | AWS deployment guide |

---

*Architecture documentation generated for WAASP v0.1.0*
