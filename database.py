"""

Database Configuration for MindBridge
PostgreSQL via asyncpg connection pool

"""
import asyncio
import json
import logging
import os
from typing import Any

import asyncpg  # postgresql driver for python
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Set database URL in your environment
#   postgresql://mb:secret@localhost:5432/mindbridge
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:PASSWORD_HERE@localhost:5432/mindbridge",
)

# underscore means private variable
# declare the pool variable as none initially
# expects an instance of a connection pool from asyncpg
# variable is either connection pool or none of pool is empty
_pool: asyncpg.pool.Pool | None = None #

# function returns instance of asyncpg.Pool
async def get_pool() -> asyncpg.Pool:
    global _pool

    if _pool is None:
        raise RuntimeError("Database pool not initialized — call init_db() first")
    return _pool

async def get_db() -> asyncpg.Connection:
    """acquire a connection from the pool. Caller must release it"""

    pool = await get_pool()
    return await pool.acquire() # acquire database connection from pool.

async def release_db(conn: asyncpg.Connection) -> None:
    """release a connection from the pool"""
    pool = await get_pool()
    await pool.release(conn) # release a database connection back to pool

# ── asyncpg needs a custom codec so JSONB columns come back as dicts ──────────

def _encode_json(value: Any) -> str:
    return json.dumps(value) # serialize obj to json formatted string

def _decode_json(value: str) -> Any:
    return json.loads(value) # deserialize str into python obj

async def init_db() -> None:
    global _pool
    logger.info("Connecting to PostgreSQL...")

    for attempt in range(10):
        try:


            _pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2, # number of connections pool is initialized with
                max_size=10, # max number of connections pool can have
                command_timeout=30,
            )

            break

        except (OSError, asyncpg.PostgresConnectionError, asyncpg.InvalidCatalogNameError) as e:
            logger.warning(f"DB not ready (attempt {attempt + 1}/10): {e}")

            if attempt < 9:
                await asyncio.sleep(3)

            else:
                raise RuntimeError("Could not connect to PostgreSQL after 10 attempts") from e


    # register JSON/JSONB codecs so Python flow in/out transparently
    async with _pool.acquire() as conn:
        await conn.set_type_codec( # set encoder/decoder pair for certain data type
            "jsonb",
            encoder=_encode_json,
            decoder=_decode_json,
            schema="pg_catalog"
        )

        await conn.set_type_codec(
            "json",
            encoder=_encode_json,
            decoder=_decode_json,
            schema="pg_catalog",
        )

        await _create_schema()
        logger.info("PostgreSQL ready")

async def close_db() -> None:
    global _pool

    if _pool:
        await _pool.close() # gracefully close all connections to pool
        _pool = None

async def _create_schema() -> None:
    """Idempotent schema creation Safe to run on every startup"""
    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                username    TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                skills      JSONB NOT NULL DEFAULT '[]',
                avatar_color TEXT NOT NULL DEFAULT '#7C3AED',
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_active TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id            TEXT PRIMARY KEY,
                title         TEXT NOT NULL,
                description   TEXT,
                host_id       TEXT NOT NULL REFERENCES users(id),
                status        TEXT NOT NULL DEFAULT 'active',
                topic         TEXT,
                urgency_level TEXT NOT NULL DEFAULT 'normal',
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ended_at      TIMESTAMPTZ,
                summary       JSONB
            );

            CREATE TABLE IF NOT EXISTS session_members (
                session_id  TEXT NOT NULL REFERENCES sessions(id),
                user_id     TEXT NOT NULL REFERENCES users(id),
                joined_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                role        TEXT NOT NULL DEFAULT 'member',
                PRIMARY KEY (session_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS signals (
                id          TEXT PRIMARY KEY,
                session_id  TEXT NOT NULL REFERENCES sessions(id),
                sender_id   TEXT NOT NULL REFERENCES users(id),
                content     TEXT NOT NULL,
                signal_type TEXT NOT NULL DEFAULT 'thought',
                topic       TEXT,
                urgency     TEXT NOT NULL DEFAULT 'normal',
                embedding   TEXT,
                routed_to   JSONB NOT NULL DEFAULT '[]',
                reactions   JSONB NOT NULL DEFAULT '{}',
                parent_id   TEXT REFERENCES signals(id),
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS memory_nodes (
                id             TEXT PRIMARY KEY,
                session_id     TEXT NOT NULL REFERENCES sessions(id),
                node_type      TEXT NOT NULL,
                content        TEXT NOT NULL,
                linked_signals JSONB NOT NULL DEFAULT '[]',
                linked_nodes   JSONB NOT NULL DEFAULT '[]',
                created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS signal_reactions (
                signal_id  TEXT NOT NULL REFERENCES signals(id),
                user_id    TEXT NOT NULL REFERENCES users(id),
                reaction   TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (signal_id, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_signals_session ON signals(session_id);
            CREATE INDEX IF NOT EXISTS idx_signals_sender  ON signals(sender_id);
            CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
        """)




