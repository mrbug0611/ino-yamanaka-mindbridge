# MindBridge 🧠

**A real-time collaborative signaling platform with NLP-powered routing**

MindBridge is a WebSocket-first team collaboration tool where participants send typed "signals" — tagged messages categorized by topic and urgency — into shared sessions. An NLP service automatically classifies each signal, determines who in the session is best suited to see it based on their skill profile, and routes it accordingly. Everyone sees the signal, but those outside the routing target receive a dimmed "shadow" view.

Inspired by Ino Yamanaka's telepathic coordination from *Naruto*.

---

## Features

- **Real-time sessions** — WebSocket-powered live collaboration rooms with presence tracking and typing indicators
- **NLP signal classification** — Each message is automatically classified by topic (bug, planning, idea, decision, review, question, urgent, general) and urgency (low, normal, high, critical)
- **Skill-based routing** — Signals are intelligently routed to session members whose skills best match the signal's content, using semantic embeddings via `sentence-transformers`
- **Signal shadowing** — Non-routed members see a dimmed version of signals so context is never completely hidden
- **Emoji reactions** — Six reaction types (⚡ 💡 ❓ ✅ 🔥 👁️) with live counts synced across the session
- **Session summaries** — On session end, the NLP service generates a structured summary with key points, action items, unresolved questions, and next steps
- **User profiles** — Persistent users with display names, avatar colors, and skill tags
- **Docker Compose deployment** — Single command to run the full stack (PostgreSQL + FastAPI + React)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, vanilla CSS-in-JS |
| Backend | FastAPI, Uvicorn, asyncpg |
| Database | PostgreSQL 16 |
| NLP | `sentence-transformers` (`all-MiniLM-L6-v2`), NumPy |
| Real-time | WebSockets (native FastAPI + Starlette) |
| Infrastructure | Docker, Docker Compose, Nginx |

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│              Browser (React)            │
│  LoginView → LobbyView → SessionView    │
│         WebSocket (useWebSocket)        │
└──────────────┬──────────────────────────┘
               │ HTTP + WebSocket
┌──────────────▼──────────────────────────┐
│         FastAPI Backend                 │
│  /api/users   /api/sessions             │
│  /api/signals /api/ws                   │
│                                         │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │  NLP Service│  │ConnectionManager │  │
│  │ classify +  │  │  WebSocket pub/  │  │
│  │  route      │  │  sub per session │  │
│  └─────────────┘  └──────────────────┘  │
│  ┌─────────────────────────────────────┐ │
│  │     BackgroundTaskManager           │ │
│  │  async FIFO queue for NLP work      │ │
│  └─────────────────────────────────────┘ │
└──────────────┬──────────────────────────┘
               │ asyncpg
┌──────────────▼──────────────────────────┐
│            PostgreSQL 16                │
│  users / sessions / session_members     │
│  signals / signal_reactions             │
└─────────────────────────────────────────┘
```

When a signal is submitted:

1. The backend NLP service classifies the content (topic + urgency)
2. Member skills are fetched from the DB and semantically compared to the signal
3. Routing targets are determined; critical signals broadcast to everyone
4. `ConnectionManager` sends the full signal to routed users and a `signal_shadow` to the rest
5. The signal is persisted to PostgreSQL

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/mindbridge.git
cd mindbridge
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
POSTGRES_DB=mindbridge
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://postgres:your_secure_password@db:5432/mindbridge

VITE_API_BASE=/api
VITE_WS_BASE=
```

> **Note:** `VITE_WS_BASE` can be left empty in production — the frontend derives the WebSocket URL from `window.location` automatically. Set it explicitly only for local development against a non-default host.

### 3. Start the stack

```bash
docker compose up --build
```

The first run downloads the `all-MiniLM-L6-v2` model (~90 MB). Subsequent starts use the Docker layer cache.

| Service | URL |
|---|---|
| Frontend | http://localhost |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/health |

### 4. Create a user and start collaborating

Open http://localhost in your browser. Enter a username to register or log back in, then create or join a session.

---

## Local Development (without Docker)

### Backend

```bash
# Python 3.10+
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://postgres:password@localhost:5432/mindbridge

# Run
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env      # edit VITE_API_BASE and VITE_WS_BASE
npm install
npm run dev               # http://localhost:5173
```

### NLP Backend Selection

The NLP service auto-detects whether `sentence-transformers` can load a model and falls back to keyword matching if it cannot. Override this with:

```bash
export MINDBRIDGE_NLP_BACKEND=keyword   # force keyword mode
export MINDBRIDGE_NLP_BACKEND=semantic  # force semantic mode
export MINDBRIDGE_EMBED_MODEL=all-MiniLM-L6-v2  # change embedding model
```

---

## Environment Variables Reference

### Root `.env`

| Variable | Description | Default |
|---|---|---|
| `POSTGRES_DB` | PostgreSQL database name | — |
| `POSTGRES_USER` | PostgreSQL username | — |
| `POSTGRES_PASSWORD` | PostgreSQL password | — |
| `DATABASE_URL` | Full asyncpg connection string | — |
| `VITE_API_BASE` | Forwarded to frontend build as API base path | `/api` |
| `VITE_WS_BASE` | Forwarded to frontend build as WebSocket base | *(derived)* |

### Backend

| Variable | Description | Default |
|---|---|---|
| `MINDBRIDGE_NLP_BACKEND` | `auto`, `semantic`, or `keyword` | `auto` |
| `MINDBRIDGE_EMBED_MODEL` | Sentence-transformers model name | `all-MiniLM-L6-v2` |

---

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# NLP classification and routing
pytest tests/test_nlp.py -v

# Background task manager
pytest tests/Test_Background.py -v --asyncio-mode=auto

# API integration tests
pytest tests/Test_Api.py -v
```

---

## Project Structure

```
mindbridge/
├── main.py                  # FastAPI app entrypoint + lifespan
├── database.py              # asyncpg connection pool
├── models.py                # Pydantic request/response models
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
│
├── routers/
│   ├── Users.py             # POST/GET /api/users
│   ├── Sessions.py          # POST/GET /api/sessions + join/end
│   ├── Signals.py           # POST/GET /api/signals + reactions
│   └── Ws.py                # WebSocket endpoint /api/ws/session/{id}/{user_id}
│
├── services/
│   ├── Nlp.py               # classify_signal, route_signal, generate_session_summary
│   ├── ConnectionManager.py # WebSocket session pub/sub, shadow routing
│   └── Background.py        # Async FIFO task queue
│
├── tests/
│   ├── test_nlp.py
│   ├── Test_Background.py
│   └── Test_Api.py
│
└── frontend/
    ├── src/
    │   ├── App.jsx           # View router (login → lobby → session)
    │   ├── api.js            # All HTTP calls to the backend
    │   ├── constants.js      # Topic styles, urgency badges, reactions
    │   ├── hooks/
    │   │   └── Usewebsocket.js  # WebSocket lifecycle hook
    │   ├── views/
    │   │   ├── LoginView.jsx    # Username lookup + registration
    │   │   ├── LobbyView.jsx    # Session list + create
    │   │   └── SessionView.jsx  # Live signal feed + send form
    │   └── components/
    │       ├── SignalCard.jsx   # Single signal with reactions
    │       ├── SummaryPanel.jsx # Session summary modal
    │       ├── Avatar.jsx
    │       ├── Badge.jsx
    │       └── Onlineusers.jsx
    ├── Dockerfile
    └── nginx.conf
```

---

## API Reference

Full interactive documentation is available at `/docs` (Swagger UI) and `/redoc` when the backend is running.

### Users

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/users` | Create a new user |
| `GET` | `/api/users/` | List users (filter by `?username=`) |
| `GET` | `/api/users/{id}` | Get a single user |

### Sessions

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/sessions/` | Create a session |
| `GET` | `/api/sessions/` | List sessions (filter by `?status=active`) |
| `GET` | `/api/sessions/{id}` | Get session details + member list |
| `POST` | `/api/sessions/{id}/join` | Join session (`?user_id=`) |
| `POST` | `/api/sessions/{id}/end` | End session and generate summary |

### Signals

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/signals/` | Submit a new signal |
| `GET` | `/api/signals/session/{id}` | Get all signals for a session |
| `GET` | `/api/signals/{id}` | Get a single signal |
| `POST` | `/api/signals/{id}/react` | Add a reaction |

### WebSocket

```
WS /api/ws/session/{session_id}/{user_id}
```

#### Inbound messages (client → server)

```json
{ "type": "typing", "is_typing": true }
```

#### Outbound messages (server → client)

| `type` | Payload | Description |
|---|---|---|
| `connected` | `online_users` | Initial presence list on connect |
| `signal` | `signal` | Full signal for routed recipients |
| `signal_shadow` | `signal`, `dimmed: true` | Dimmed signal for non-routed members |
| `reaction` | `signal_id`, `reactions` | Updated reaction counts |
| `user_joined` | `online_users` | A user connected |
| `user_left` | `online_users` | A user disconnected |
| `typing` | `user_id`, `is_typing` | Typing indicator |
| `session_ended` | — | Host ended the session |

---

## Signal Topics & Urgency

| Topic | Description |
|---|---|
| `bug` | Errors, crashes, broken behaviour |
| `planning` | Roadmaps, sprints, milestones |
| `idea` | Proposals, brainstorms, experiments |
| `decision` | Choices that need consensus |
| `review` | Code review, approval requests |
| `question` | Clarifications and how-to queries |
| `urgent` | Critical issues needing immediate action |
| `general` | Everything else |

| Urgency | Routing behaviour |
|---|---|
| `low` | Skill-matched routing |
| `normal` | Skill-matched routing |
| `high` | Skill-matched routing + sender always included |
| `critical` | Broadcast to **all** session members |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run tests before opening a PR: `pytest tests/ -v`
4. Open a pull request against `main`

Code review is automated via CodeRabbit (`.coderabbit.yaml`).

---

## License

MIT
