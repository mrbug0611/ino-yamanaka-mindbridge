# MindBridge — Architecture Reference

This document describes the internal design of MindBridge in enough detail to onboard a new contributor or to make confident changes to any subsystem.

---

## Table of Contents

- [System Overview](#system-overview)
- [Backend](#backend)
  - [Startup & Lifespan](#startup--lifespan)
  - [Database Layer](#database-layer)
  - [Data Models](#data-models)
  - [Routers](#routers)
  - [WebSocket & ConnectionManager](#websocket--connectionmanager)
  - [NLP Service](#nlp-service)
  - [BackgroundTaskManager](#backgroundtaskmanager)
- [Frontend](#frontend)
  - [View Routing](#view-routing)
  - [API Module](#api-module)
  - [WebSocket Hook](#websocket-hook)
  - [Components](#components)
- [Signal Lifecycle](#signal-lifecycle)
- [Session Lifecycle](#session-lifecycle)
- [Data Schema](#data-schema)
- [Configuration Reference](#configuration-reference)

---

## System Overview

MindBridge is a three-tier web application:

```
Browser  ──HTTP/WS──►  FastAPI  ──asyncpg──►  PostgreSQL
```

- The **frontend** (React + Vite, served by Nginx in Docker) is a single-page application with three views: Login, Lobby, and Session.
- The **backend** (FastAPI + Uvicorn) exposes a REST API and a WebSocket endpoint. A singleton `ConnectionManager` tracks open WebSocket connections indexed by session and user. An NLP service classifies and routes every incoming signal.
- **PostgreSQL** stores users, sessions, session membership, signals, and per-signal emoji reactions.

In Docker Compose the three services (`db`, `backend`, `frontend`) talk over a shared bridge network. Nginx proxies `/api` and `/api/ws` to the backend, so the frontend only ever needs a single origin.

---

## Backend

### Startup & Lifespan

`main.py` uses FastAPI's `@asynccontextmanager` lifespan to sequence startup and shutdown:

1. `init_db()` — creates the asyncpg connection pool and runs `CREATE TABLE IF NOT EXISTS` for all tables
2. `BackgroundTaskManager.start()` — spins up the async worker queue
3. `get_classifier()` — warms the sentence-transformers model so the first request is not slow
4. *(on shutdown)* `BackgroundTaskManager.stop()` → `close_db()`

This ensures the NLP model is loaded exactly once into process memory, shared across all request handlers.

### Database Layer

`database.py` manages a single `asyncpg.Pool`. All backend code acquires and releases connections through two helpers:

```python
conn = await get_db()      # acquire from pool
# ...
await release_db(conn)     # return to pool
```

Always release in a `finally` block. The pool size is configured via `asyncpg.create_pool()` defaults (min 1, max 10 by default).

**Table initialization** is declarative: `init_db()` contains raw `CREATE TABLE IF NOT EXISTS` statements. There is no migration framework. Schema changes require manual `ALTER TABLE` for existing databases, or dropping and recreating via Docker volume reset.

### Data Models

All Pydantic models live in `models.py`:

| Model | Purpose |
|---|---|
| `UserCreate` / `UserResponse` | Create and retrieve users |
| `SessionCreate` / `SessionResponse` | Create and retrieve sessions (includes member list) |
| `SessionSummary` | Structured output from `generate_session_summary` |
| `SignalCreate` / `SignalResponse` | Submit and retrieve signals (includes sender name/color via JOIN) |
| `ReactionAdd` | Add an emoji reaction (validated against the allowed set) |
| `ClassificationResult` | NLP output: topic, urgency, signal_type, routing targets, confidence |
| `WSMessage` / `WSSignalBroadcast` | WebSocket envelope types |

`gen_id()` returns `str(uuid.uuid4())` — all primary keys are UUID strings, not auto-increment integers.

### Routers

Four routers are mounted under `/api`:

#### `routers/Users.py` — `/api/users`

Standard CRUD. Username uniqueness is enforced at the DB level with a UNIQUE constraint; the router catches the resulting `asyncpg.UniqueViolationError` and raises `HTTP 409`.

Users persist across sessions and are looked up by username on the login screen.

#### `routers/Sessions.py` — `/api/sessions`

- `POST /` — creates a session and adds the host as a `session_members` row with `role='host'`
- `POST /{id}/join` — adds a user to `session_members` with `role='member'`
- `POST /{id}/end` — sets `status='ended'`, calls `generate_session_summary()` with all signals for the session, stores the JSON summary, and broadcasts `session_ended` over WebSocket

The helper `_get_session(conn, session_id)` is reused across all endpoints and returns a fully hydrated `SessionResponse` including the member list.

#### `routers/Signals.py` — `/api/signals`

The most complex router. `POST /` does the following:

1. Calls `classify_signal(content)` from the NLP service
2. Fetches session member skills from the DB
3. Calls `route_signal(topic, urgency, members, sender_id, content)` to determine routing targets
4. Inserts the signal row (with topic, urgency, routed_to as a JSON array)
5. Calls `ConnectionManager.broadcast_to_routed()` to push the signal over WebSocket
6. Returns the persisted `SignalResponse`

Reactions (`POST /{id}/react`) insert into `signal_reactions` and immediately broadcast updated reaction counts to the session.

#### `routers/Ws.py` — `/api/ws`

Single endpoint: `WS /session/{session_id}/{user_id}`.

On connect: registers the socket in `ConnectionManager`, broadcasts `user_joined` presence update.

Message loop: handles `typing` messages from the client and re-broadcasts them to the session.

On disconnect: removes from `ConnectionManager`, broadcasts `user_left`.

### WebSocket & ConnectionManager

`services/ConnectionManager.py` is a singleton (`manager = ConnectionManager()`) shared across all router modules.

Internal state:

```python
_sessions: dict[str, dict[str, WebSocket]]  # session_id → {user_id → ws}
_user_sessions: dict[str, str]              # user_id → session_id (reverse lookup)
_lock: asyncio.Lock
```

Key methods:

| Method | Description |
|---|---|
| `connect(ws, session_id, user_id)` | Accept and register a WebSocket |
| `disconnect(session_id, user_id)` | Remove from both dicts |
| `broadcast_to_session(session_id, msg, exclude_user)` | Fan-out to all members |
| `send_to_user(session_id, user_id, msg)` | Point-to-point delivery |
| `broadcast_to_routed(session_id, routed_to, msg, sender_id)` | Full signal to targets, shadow to everyone else |

Dead connections detected during a send are cleaned up immediately in `broadcast_to_session`.

### NLP Service

`services/Nlp.py` provides three public functions:

#### `classify_signal(content: str) -> dict`

Returns `{ topic, urgency, signal_type, confidence }`.

The service runs in one of two modes, auto-selected at import time:

**Semantic mode** (preferred, requires `sentence-transformers`):
- Loads `all-MiniLM-L6-v2` once via `get_classifier()`
- Encodes topic exemplars once at startup into a matrix of vectors
- On each call, encodes the incoming content and computes cosine similarity against every exemplar, picking the topic with the highest average similarity
- Confidence is the similarity score of the winning topic

**Keyword mode** (fallback):
- Counts keyword matches from `TOPIC_KEYWORDS` per topic
- Falls back to `general` when no keywords match

Urgency is detected from a separate keyword list and heuristics regardless of which backend is active.

Override backend selection: `MINDBRIDGE_NLP_BACKEND=keyword|semantic|auto`

#### `route_signal(topic, urgency, members, sender_id, content) -> list[str]`

Returns a list of user IDs that should receive the full signal.

- `critical` urgency → all member IDs
- Otherwise: for each member, compute a skill-match score (semantic similarity between the signal content and the member's skill tags). Members above the similarity threshold are included. The sender is always included.

#### `generate_session_summary(signals: list[dict]) -> dict`

Produces a `SessionSummary`-shaped dict:

- `key_points` — the most representative signals, deduplicated by semantic clustering (`extract_key_sentences`)
- `unresolved_questions` — signals classified as `question` with no `✅` reaction
- `action_items` — signals with `✅` reactions
- `next_steps` — signals tagged `planning`
- `topic_clusters` — count distribution of signal topics

### BackgroundTaskManager

`services/Background.py` provides a simple async FIFO queue for fire-and-forget work:

```python
manager = BackgroundTaskManager()
await manager.start()
await manager.enqueue(some_coroutine())
```

A single `asyncio.Task` worker pulls coroutines from the queue and `await`s them sequentially. Exceptions are logged and discarded; the worker continues. This prevents NLP work from blocking a request handler while ensuring signals are processed in order.

---

## Frontend

### View Routing

`App.jsx` is a pure state machine with three states: `"login"`, `"lobby"`, `"session"`. Shared state threaded through the tree:

- `user` — the logged-in user object (persisted across session changes)
- `activeSession` — the current session object
- `sessionSignals` — the snapshot of signals loaded when joining (subsequent signals arrive via WebSocket)

Transitions:

```
login ──onLogin──► lobby ──onJoinSession──► session
                   ▲                              │
                   └─────────onLeave──────────────┘
login ◄───onLogout───────────────────────────────┘
```

### API Module

`src/api.js` centralises all HTTP calls. The base URL is read from `VITE_API_BASE` (defaulting to `/api`), so the same build works behind Nginx in Docker and directly against `localhost:8000` in development.

Each function returns a parsed JSON object or throws on non-OK responses. Callers handle errors with `try/catch`.

### WebSocket Hook

`src/hooks/Usewebsocket.js` exports `useWebSocket({ onSignal, onReactionUpdate, onPresenceChange, onTypingChange, onSessionEnded })`.

Key design decisions:

- Callbacks are stored in refs (`onSignalRef`, etc.) so `ws.onmessage` always calls the latest callback version without needing to close and reopen the connection on re-renders
- `connect(sessionId, userId)` closes any existing socket before opening a new one
- `notifyTyping()` debounces typing events and sends `{ type: "typing", is_typing: false }` 2 seconds after the last keystroke
- The hook returns `{ connect, disconnect, notifyTyping, send }`

### Components

| Component | Props | Purpose |
|---|---|---|
| `SignalCard` | `signal`, `currentUserId`, `onReact`, `isNew`, `dimmed` | Renders a single signal with topic/urgency badges, reactions, and a slide-in animation for new signals |
| `SummaryPanel` | `summary`, `onClose` | Modal overlay showing the session summary broken into sections |
| `Avatar` | `name`, `color`, `size` | Coloured circle with initials |
| `Badge` | `label`, `style` | Small pill label |
| `OnlineUsers` | `onlineIds`, `members` | Row of avatars for currently connected members |

---

## Signal Lifecycle

```
User types in SessionView
        │
        ▼
POST /api/signals/  (SignalCreate)
        │
        ├──► classify_signal(content)     → topic, urgency, confidence
        │
        ├──► fetch member skills from DB
        │
        ├──► route_signal(...)            → routed_to: [user_id, ...]
        │
        ├──► INSERT INTO signals
        │
        ├──► ConnectionManager.broadcast_to_routed()
        │         │
        │         ├── full "signal" message → routed users + sender
        │         └── "signal_shadow" (dimmed:true) → everyone else
        │
        └──► return SignalResponse to HTTP caller
```

On the frontend:
- Routed users see the signal rendered normally in `SignalCard`
- Non-routed users see it with `opacity: 0.55` and greyed-out text (`dimmed` prop)
- New signals trigger a 0.8-second `slideIn` CSS animation

---

## Session Lifecycle

```
Host: POST /api/sessions/       → session created, host added as member
Host: WS connect                → ConnectionManager registers host
Others: POST /sessions/{id}/join
Others: WS connect              → presence broadcast to session
...
[signals exchanged]
...
Host: POST /sessions/{id}/end
        │
        ├──► generate_session_summary(all signals)
        ├──► UPDATE sessions SET status='ended', summary=...
        └──► broadcast "session_ended" to all WS connections
                └──► SessionView shows SummaryPanel overlay
```

---

## Data Schema

```sql
CREATE TABLE users (
    id           TEXT PRIMARY KEY,
    username     TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    skills       JSONB DEFAULT '[]',
    avatar_color TEXT DEFAULT '#7C3AED',
    created_at   TIMESTAMPTZ DEFAULT now(),
    last_active  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE sessions (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    description   TEXT,
    host_id       TEXT REFERENCES users(id),
    status        TEXT DEFAULT 'active',
    topic         TEXT,
    urgency_level TEXT DEFAULT 'normal',
    created_at    TIMESTAMPTZ DEFAULT now(),
    ended_at      TIMESTAMPTZ,
    summary       JSONB
);

CREATE TABLE session_members (
    session_id TEXT REFERENCES sessions(id),
    user_id    TEXT REFERENCES users(id),
    role       TEXT DEFAULT 'member',
    joined_at  TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (session_id, user_id)
);

CREATE TABLE signals (
    id          TEXT PRIMARY KEY,
    session_id  TEXT REFERENCES sessions(id),
    sender_id   TEXT REFERENCES users(id),
    content     TEXT NOT NULL,
    signal_type TEXT DEFAULT 'thought',
    topic       TEXT,
    urgency     TEXT DEFAULT 'normal',
    routed_to   JSONB DEFAULT '[]',
    reactions   JSONB DEFAULT '{}',
    parent_id   TEXT REFERENCES signals(id),
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE signal_reactions (
    signal_id TEXT REFERENCES signals(id),
    user_id   TEXT REFERENCES users(id),
    reaction  TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (signal_id, user_id, reaction)
);
```

---

## Configuration Reference

| Variable | Where set | Effect |
|---|---|---|
| `DATABASE_URL` | `.env` / Docker | asyncpg connection string |
| `POSTGRES_*` | `.env` | Passed to the PostgreSQL container |
| `MINDBRIDGE_NLP_BACKEND` | `.env` / shell | `auto` (default), `semantic`, or `keyword` |
| `MINDBRIDGE_EMBED_MODEL` | `.env` / shell | Sentence-transformers model name |
| `HF_HUB_DISABLE_IMPLICIT_TOKEN` | Set in `Nlp.py` | Prevents unintended authenticated HuggingFace requests |
| `VITE_API_BASE` | `frontend/.env` / Docker build arg | HTTP API base path for the frontend |
| `VITE_WS_BASE` | `frontend/.env` / Docker build arg | WebSocket base URL (auto-derived if empty) |
