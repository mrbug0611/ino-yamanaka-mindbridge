"""Sessions API Router"""
import json

from fastapi import APIRouter, HTTPException, Query

from database import get_db, release_db
from models import SessionCreate, SessionResponse, gen_id
from services.Nlp import generate_session_summary

router = APIRouter()


async def _get_session(conn, session_id: str) -> SessionResponse:

    record = await conn.fetchrow("SELECT * FROM sessions WHERE id = $1", session_id)

    if not record:
        raise HTTPException(status_code=404, detail="Session not found")

    member_rows = await conn.fetch(
        """
        SELECT u.id, u.display_name, u.avatar_color, u.skills, sm.role
        FROM session_members sm
        JOIN users u ON sm.user_id = u.id
        WHERE sm.session_id = $1
        """,
        session_id,
    )

    members = []

    for m in member_rows:
        skills = m["skills"]

        if isinstance(skills, str):
            skills = json.loads(skills)

        members.append({
            "id": m["id"],
            "display_name": m["display_name"],
            "avatar_color": m["avatar_color"],
            "skills": skills,
            "role": m["role"],
        })

    summary = record["summary"]

    if isinstance(summary, str):
        summary = json.loads(summary)

    return SessionResponse(
        id=record["id"],
        title=record["title"],
        description=record["description"],
        host_id=record["host_id"],
        status=record["status"],
        topic=record["topic"],
        urgency_level=record["urgency_level"],
        created_at=str(record["created_at"]),
        ended_at=str(record["ended_at"]) if record["ended_at"] else None,
        summary=summary,
        member_count=len(members),
        members=members,
    )



@router.post("/", response_model=SessionResponse)
async def create_session(session: SessionCreate):
    conn = await get_db()

    try:
        session_id = gen_id()
        await conn.execute(
            """
            INSERT INTO sessions (id, title, description, host_id, topic)
            VALUES ($1, $2, $3, $4, $5)
            """,
            session_id, session.title, session.description,
            session.host_id, session.topic,
        )
        await conn.execute(
            "INSERT INTO session_members (session_id, user_id, role) VALUES ($1, $2, 'host')",
            session_id, session.host_id,
        )

        return await _get_session(conn, session_id)
    finally:
        await release_db(conn)

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    conn = await get_db()

    try:
        return await _get_session(conn, session_id)
    finally:
        await release_db(conn)

@router.get("/", response_model=list[SessionResponse])
async def list_sessions(status: str | None = Query(None)): # function argument HTTP query parameter default set none
    conn = await get_db()

    try:
        if status:
            rows = await conn.fetch(
                "SELECT id FROM sessions WHERE status = $1 ORDER BY created_at DESC LIMIT 50",
                status,
            )
        else:
            rows = await conn.fetch(
                "SELECT id FROM sessions ORDER BY created_at DESC LIMIT 50"
            )

        result = []

        for r in rows:
            result.append(await _get_session(conn, r["id"]))
        return result
    finally:
        await release_db(conn)

@router.post("/{session_id}/join")
async def join_session(session_id: str, user_id: str):
    conn = await get_db()

    try:
        row = await conn.fetchrow(
            "SELECT id, status FROM sessions WHERE id = $1", session_id
        )

        if not row:
            raise HTTPException(status_code=404, detail="Session not found")

        if row["status"] != "active":
            raise HTTPException(status_code=400, detail="Session not active")

        # INSERT ... ON CONFLICT DO NOTHING is the Postgres equivalent of INSERT OR IGNORE
        await conn.execute(
            """
            INSERT INTO session_members (session_id, user_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            session_id, user_id,
        )
        return {"status": "joined", "session_id": session_id, "user_id": user_id}
    finally:
        await release_db(conn)

@router.post("/{session_id}/end")
async def end_session(session_id: str):
    conn = await get_db()

    try:
        rows = await conn.fetch(
            """
            SELECT s.*, u.display_name AS sender_name
            FROM signals s
            JOIN users u ON s.sender_id = u.id
            WHERE s.session_id = $1
            ORDER BY s.created_at
            """,
            session_id,
        )

        signals = []
        for r in rows:
            d = dict(r)

             # routed_to and reactions are already dicts/lists from JSONB codec
            if isinstance(d.get("routed_to"), str):
                d["routed_to"] = json.loads(d["routed_to"])

            if isinstance(d.get("reactions"), str):
                d["reactions"] = json.loads(d["reactions"])
            signals.append(d)

        summary = generate_session_summary(signals)

        await conn.execute(
            """
            UPDATE sessions
            SET status = 'ended', ended_at = NOW(), summary = $1::jsonb
            WHERE id = $2
            """,
            json.dumps(summary), session_id,
        )
        return {"status": "ended", "session_id": session_id, "summary": summary}
    finally:
        await release_db(conn)


