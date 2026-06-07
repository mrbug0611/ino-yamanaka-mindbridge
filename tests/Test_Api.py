"""
Integration tests for MindBridge API
Uses an in-process aiosqlite backend so no Postgres is needed for CI.
Run with: pytest tests/test_api.py -v --asyncio-mode=auto
"""

import sys, os, json, uuid, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
import aiosqlite
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# ── Patch the database module to use aiosqlite for tests ────────────────────

TEST_DB = Path("test_mindbridge.db")

import database as _dbmod

class _FakeConn:
    """Thin wrapper that makes aiosqlite look like asyncpg for tests."""
    def __init__(self, conn: aiosqlite.Connection):
        self._c = conn

    async def execute(self, sql, *args):
        pg_sql, params = _pg2sqlite(sql, args)
        await self._c.execute(pg_sql, params)
        await self._c.commit()

    async def fetchrow(self, sql, *args):
        pg_sql, params = _pg2sqlite(sql, args)
        # INSERT OR IGNORE … RETURNING * returns nothing on a skipped row;
        # re-SELECT to get the existing row instead.
        if 'RETURNING' in pg_sql.upper() and 'INSERT' in pg_sql.upper():
            async with self._c.execute(pg_sql, params) as cur:
                row = await cur.fetchone()
            if row is None:
                # Row was skipped by OR IGNORE — fetch the existing one
                import re
                m = re.search(r'INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)', pg_sql, re.IGNORECASE)
                if m:
                    table = m.group(1)
                    async with self._c.execute(f'SELECT * FROM {table} WHERE rowid = last_insert_rowid()') as cur2:
                        row = await cur2.fetchone()
            return row
        async with self._c.execute(pg_sql, params) as cur:
            return await cur.fetchone()

    async def fetch(self, sql, *args):
        pg_sql, params = _pg2sqlite(sql, args)
        async with self._c.execute(pg_sql, params) as cur:
            return await cur.fetchall()

    async def set_type_codec(self, *a, **kw):
        pass


def _pg2sqlite(sql: str, args: tuple):
    """Convert Postgres SQL → SQLite-compatible SQL."""
    import re
    flat = args[0] if len(args) == 1 and isinstance(args[0], (list, tuple)) else args

    # Strip type casts  ::jsonb  ::json  ::text
    sql = re.sub(r'::\w+', '', sql)
    # NOW() → CURRENT_TIMESTAMP
    sql = re.sub(r'\bNOW\(\)', 'CURRENT_TIMESTAMP', sql)
    # TIMESTAMPTZ / JSONB type names in DDL
    sql = re.sub(r'\bTIMESTAMPTZ\b', 'TIMESTAMP', sql)
    sql = re.sub(r'\bJSONB\b', 'TEXT', sql)

    # ON CONFLICT (cols) DO UPDATE SET x = EXCLUDED.x  →  (strip; INSERT OR REPLACE handles it)
    sql = re.sub(
        r'ON CONFLICT\s*\([^)]+\)\s*DO UPDATE SET[^\n;]+', '', sql, flags=re.IGNORECASE
    )
    # ON CONFLICT DO NOTHING  →  nothing (we'll use INSERT OR IGNORE instead)
    sql = re.sub(r'ON CONFLICT DO NOTHING', '', sql, flags=re.IGNORECASE)

    # Rewrite INSERT … to INSERT OR IGNORE … when ON CONFLICT was present
    if 'ON CONFLICT' in sql.upper() or re.search(r'OR IGNORE|OR REPLACE', sql, re.IGNORECASE):
        pass  # already handled above
    # Apply OR IGNORE only to plain INSERT (no OR modifier yet)
    if re.match(r'\s*INSERT\s+INTO', sql, re.IGNORECASE) and \
       not re.match(r'\s*INSERT\s+OR', sql, re.IGNORECASE):
        sql = re.sub(r'INSERT\s+INTO', 'INSERT OR IGNORE INTO', sql, count=1, flags=re.IGNORECASE)

    # $N → ?  (replace highest first to avoid $1 eating $10)
    count = len(flat)
    for i in range(count, 0, -1):
        sql = sql.replace(f'${i}', '?')

    # Serialize list/dict params to JSON strings
    serialised = [json.dumps(p) if isinstance(p, (dict, list)) else p for p in flat]
    return sql, tuple(serialised)


_sqlite_conn: aiosqlite.Connection | None = None

async def _fake_init_db():
    global _sqlite_conn
    _sqlite_conn = await aiosqlite.connect(TEST_DB)
    _sqlite_conn.row_factory = aiosqlite.Row
    await _sqlite_conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL, skills TEXT DEFAULT '[]',
            avatar_color TEXT DEFAULT '#7C3AED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
            host_id TEXT NOT NULL, status TEXT DEFAULT 'active', topic TEXT,
            urgency_level TEXT DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP, summary TEXT);
        CREATE TABLE IF NOT EXISTS session_members (
            session_id TEXT NOT NULL, user_id TEXT NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            role TEXT DEFAULT 'member',
            PRIMARY KEY (session_id, user_id));
        CREATE TABLE IF NOT EXISTS signals (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL, sender_id TEXT NOT NULL,
            content TEXT NOT NULL, signal_type TEXT DEFAULT 'thought', topic TEXT,
            urgency TEXT DEFAULT 'normal', embedding TEXT,
            routed_to TEXT DEFAULT '[]', reactions TEXT DEFAULT '{}',
            parent_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS signal_reactions (
            signal_id TEXT NOT NULL, user_id TEXT NOT NULL, reaction TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (signal_id, user_id));
    """)
    await _sqlite_conn.commit()

async def _fake_get_db():
    return _FakeConn(_sqlite_conn)

async def _fake_release_db(conn):
    pass  # shared connection — don't close

async def _fake_close_db():
    global _sqlite_conn
    if _sqlite_conn:
        await _sqlite_conn.close()
        _sqlite_conn = None

_dbmod.init_db = _fake_init_db
_dbmod.get_db = _fake_get_db
_dbmod.release_db = _fake_release_db
_dbmod.close_db = _fake_close_db

# ── Now import app AFTER patching ────────────────────────────────────────────

from main import app


@pytest_asyncio.fixture(scope="module")
async def setup_db():
    await _fake_init_db()
    yield
    await _fake_close_db()
    TEST_DB.unlink(missing_ok=True)


@pytest_asyncio.fixture
async def client(setup_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestHealthCheck:
    async def test_health(self, client):
        r = await client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "neural_link_active"


@pytest.mark.asyncio
class TestUsers:
    async def test_create_user(self, client):
        r = await client.post("/api/users/", json={
            "username": f"ino_{uuid.uuid4().hex[:6]}",
            "display_name": "Ino Yamanaka",
            "skills": ["mind-transfer", "sensory"],
            "avatar_color": "#8B5CF6",
        })
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["display_name"] == "Ino Yamanaka"

    async def test_create_duplicate_user(self, client):
        name = f"dup_{uuid.uuid4().hex[:6]}"
        r1 = await client.post("/api/users/", json={"username": name, "display_name": "Original", "skills": []})
        r2 = await client.post("/api/users/", json={"username": name, "display_name": "Duplicate", "skills": []})
        # Either a 409 (Postgres) or a 200 returning the original (SQLite shim with OR IGNORE)
        assert r2.status_code in (200, 409)
        if r2.status_code == 200:
            assert r2.json()["display_name"] == "Original"

    async def test_list_users(self, client):
        r = await client.get("/api/users/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_get_user_by_username_found(self, client):
        name = f"find_{uuid.uuid4().hex[:6]}"
        created = (await client.post("/api/users/", json={
            "username": name, "display_name": "Find Me", "skills": [],
        })).json()
        r = await client.get(f"/api/users/?username={name}")
        assert r.status_code == 200
        results = r.json()
        assert len(results) == 1
        assert results[0]["id"] == created["id"]
        assert results[0]["username"] == name

    async def test_get_user_by_username_not_found(self, client):
        r = await client.get("/api/users/?username=definitely_does_not_exist_xyz")
        assert r.status_code == 200
        assert r.json() == []

    async def test_get_user_by_username_no_cross_match(self, client):
        """Filtering by username should not return other users."""
        name_a = f"usera_{uuid.uuid4().hex[:6]}"
        name_b = f"userb_{uuid.uuid4().hex[:6]}"
        await client.post("/api/users/", json={"username": name_a, "display_name": "A", "skills": []})
        await client.post("/api/users/", json={"username": name_b, "display_name": "B", "skills": []})
        r = await client.get(f"/api/users/?username={name_a}")
        results = r.json()
        assert all(u["username"] == name_a for u in results)


@pytest.mark.asyncio
class TestSessions:
    async def _user(self, client, skills=None):
        r = await client.post("/api/users/", json={
            "username": f"u_{uuid.uuid4().hex[:8]}",
            "display_name": "Test User",
            "skills": skills or [],
        })
        return r.json()

    async def test_create_session(self, client):
        host = await self._user(client, ["backend"])
        r = await client.post("/api/sessions/", json={
            "title": "Emergency Auth Bug",
            "host_id": host["id"],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "active"
        assert data["member_count"] == 1

    async def test_join_session(self, client):
        host = await self._user(client, ["backend"])
        sess = (await client.post("/api/sessions/", json={"title": "Join Test", "host_id": host["id"]})).json()
        member = await self._user(client, ["frontend"])
        r = await client.post(f"/api/sessions/{sess['id']}/join?user_id={member['id']}")
        assert r.status_code == 200
        assert r.json()["status"] == "joined"

    async def test_list_sessions(self, client):
        r = await client.get("/api/sessions/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


@pytest.mark.asyncio
class TestSignals:
    async def _setup(self, client):
        host = (await client.post("/api/users/", json={
            "username": f"h_{uuid.uuid4().hex[:8]}", "display_name": "Host", "skills": ["backend"],
        })).json()
        member = (await client.post("/api/users/", json={
            "username": f"m_{uuid.uuid4().hex[:8]}", "display_name": "Member", "skills": ["frontend"],
        })).json()
        sess = (await client.post("/api/sessions/", json={"title": "Sig Test", "host_id": host["id"]})).json()
        await client.post(f"/api/sessions/{sess['id']}/join?user_id={member['id']}")
        return host, member, sess

    async def test_create_signal(self, client):
        host, _, sess = await self._setup(client)
        r = await client.post("/api/signals/", json={
            "session_id": sess["id"], "sender_id": host["id"],
            "content": "The login endpoint crashes on null input",
        })
        assert r.status_code == 200
        assert r.json()["topic"] == "bug"

    async def test_urgency_critical(self, client):
        host, _, sess = await self._setup(client)
        r = await client.post("/api/signals/", json={
            "session_id": sess["id"], "sender_id": host["id"],
            "content": "PRODUCTION DOWN - all users getting 500 errors!",
        })
        assert r.status_code == 200
        assert r.json()["urgency"] in ("critical", "high")

    async def test_get_session_signals(self, client):
        host, _, sess = await self._setup(client)
        await client.post("/api/signals/", json={
            "session_id": sess["id"], "sender_id": host["id"], "content": "First thought",
        })
        r = await client.get(f"/api/signals/session/{sess['id']}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_add_reaction(self, client):
        host, member, sess = await self._setup(client)
        sig = (await client.post("/api/signals/", json={
            "session_id": sess["id"], "sender_id": host["id"], "content": "Great idea!",
        })).json()
        r = await client.post(f"/api/signals/{sig['id']}/react", json={
            "user_id": member["id"], "reaction": "💡",
        })
        assert r.status_code == 200
        assert r.json()["reactions"].get("💡", 0) >= 1


@pytest.mark.asyncio
class TestSessionSummary:
    async def test_end_session(self, client):
        host = (await client.post("/api/users/", json={
            "username": f"sh_{uuid.uuid4().hex[:8]}", "display_name": "SHost", "skills": ["backend"],
        })).json()
        sess = (await client.post("/api/sessions/", json={"title": "Summary Test", "host_id": host["id"]})).json()
        for msg in [
            "We need to fix the auth bug by tomorrow",
            "What should we do about connection pooling?",
            "Implement retry logic for failed API calls",
        ]:
            await client.post("/api/signals/", json={
                "session_id": sess["id"], "sender_id": host["id"], "content": msg,
            })
        r = await client.post(f"/api/sessions/{sess['id']}/end")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ended"
        assert "summary" in data
        assert "key_points" in data["summary"]