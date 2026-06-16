# Changelog

All notable changes to MindBridge will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Planned
- Persistent authentication (JWT or session cookies) to replace username-only login
- Frontend test suite (Vitest + React Testing Library)
- Message threading (parent signals already supported in the schema)
- Configurable NLP routing threshold per session
- Rate limiting on signal submission

---

## [1.0.0] — Initial Release

### Added
- Real-time session collaboration over WebSockets
- NLP signal classification (topic + urgency) using `sentence-transformers` with keyword fallback
- Skill-based semantic routing — signals reach the members best positioned to act on them
- Signal shadowing — non-routed members see a dimmed version, never a blank feed
- Six emoji reactions (⚡ 💡 ❓ ✅ 🔥 👁️) with live sync across the session
- Session summary generation on session end (key points, action items, unresolved questions, next steps, topic distribution)
- User profiles with display name, skill tags, and avatar colour
- Lobby view with session list, create form, and join flow
- Typing indicators over WebSocket
- Presence tracking (online users panel)
- Docker Compose deployment (PostgreSQL 16 + FastAPI + React/Nginx)
- Swagger UI at `/docs` and ReDoc at `/redoc`
- Health check endpoint at `/api/health`
- Test suites for NLP service, background task manager, and API integration
- CodeRabbit automated code review configuration
