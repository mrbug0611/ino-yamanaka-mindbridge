"""Signals API router - the core thought capture and routing engine"""
import json
from typing import List

from fastapi import APIRouter, HTTPException

from database import get_db, release_db
from models import SignalResponse, SignalCreate, gen_id, ReactionAdd
from services.Nlp import classify_signal, route_signal
from services.ConnectionManager import manager
router = APIRouter()


def _row_to_signal(row, reactions: dict = None) -> SignalResponse:
    routed_to = row["routed_to"]

    if isinstance(routed_to, str):
        routed_to = json.loads(routed_to)

    stored_reactions = row["reactions"] or {}
    if isinstance(stored_reactions, str):
        stored_reactions = json.loads(stored_reactions)
    if reactions is not None:
        stored_reactions = reactions

    return SignalResponse(
        id=row["id"],
        session_id=row["session_id"],
        sender_id=row["sender_id"],
        sender_name=row["sender_name"],
        sender_color=row["sender_color"],
        content=row["content"],
        signal_type=row["signal_type"],
        topic=row["topic"],
        urgency=row["urgency"],
        routed_to=routed_to,
        reactions=stored_reactions,
        parent_id=row["parent_id"],
        created_at=str(row["created_at"]),
    )


async def _get_signal(conn, signal_id: str) -> SignalResponse:
    row = await conn.fetchrow(
        """
        SELECT s.*, u.display_name AS sender_name, u.avatar_color AS sender_color
        FROM signals s
        JOIN users u ON s.sender_id = u.id
        WHERE s.id = $1
        """,
        signal_id,
    )

    if not row:
        raise HTTPException(status_code=404, detail="Signal not found")

    reaction_rows = await conn.fetch(
        """
        SELECT reaction, COUNT(*) AS cnt
        FROM signal_reactions
        WHERE signal_id = $1
        GROUP BY reaction
        """,
        signal_id,
    )

    reactions = {r["reaction"]: r["cnt"] for r in reaction_rows}
    return _row_to_signal(row, reactions)

@router.post("/", response_model=SignalResponse)
async def create_signal(signal: SignalCreate):
    conn = await get_db()

    try:
        # Classify with NLP
        classification = classify_signal(signal.content)

        # Get session members for routing
        member_rows = await conn.fetch(
            """
            SELECT u.id, u.skills
            FROM session_members sm
            JOIN users u ON sm.user_id = u.id
            WHERE sm.session_id = $1
            """,
            signal.session_id,
        )

        members = []

        for r in member_rows:
            skills = r["skills"]
            if isinstance(skills, str):
                skills = json.loads(skills)
            members.append({"id": r["id"], "skills": skills})

        # Route Signal
        routed_to = route_signal(
            topic=classification["topic"],
            urgency=classification["urgency"],
            members=members,
            sender_id=signal.sender_id,
            content=signal.content,
        )

        # persist signal - routed_to stored as jsonb
        signal_id = gen_id()
        await conn.execute(
            """
            INSERT INTO signals
                (id, session_id, sender_id, content, signal_type, topic,
                 urgency, routed_to, parent_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)
            """,
            signal_id, signal.session_id, signal.sender_id, signal.content,
            classification["signal_type"], classification["topic"],
            classification["urgency"], json.dumps(routed_to), signal.parent_id,
        )

        # bump session urgency if elevated
        if classification["urgency"] in ("critical", "high"):
            await conn.execute(
                """
                UPDATE sessions
                SET urgency_level = $1
                WHERE id = $2 AND urgency_level != 'critical'
                """,
                classification["urgency"], signal.session_id,
            )

        # fetch full signal for response
        response = await _get_signal(conn, signal_id)

        # broadcast via websocket
        ws_message = {
            "type": "signal",
            "signal": response.model_dump(),
            "routing": routed_to,
            "urgency": classification["urgency"],
        }

        if classification["urgency"] == "critical":
            await manager.broadcast_to_session(signal.session_id, ws_message)
        else:
            await manager.broadcast_to_routed(
                signal.session_id, routed_to, ws_message,
                sender_id=signal.sender_id,
            )

        return response

    finally:
        await release_db(conn)


@router.get("/session/{session_id}", response_model=List[SignalResponse])
async def get_session_signals(session_id: str, limit: int = 100):
    conn = await get_db()

    try:
        rows = await conn.fetch(
            """
            SELECT s.*, u.display_name AS sender_name, u.avatar_color AS sender_color
            FROM signals s
            JOIN users u ON s.sender_id = u.id
            WHERE s.session_id = $1
            ORDER BY s.created_at ASC
            LIMIT $2
            """,
            session_id, limit,
        )

        return [_row_to_signal(r) for r in rows]
    finally:
        await release_db(conn)

@router.post("/{signal_id}/react")
async def add_reaction(signal_id: str, reaction: ReactionAdd):
    conn = await get_db()

    try:
        row = await conn.fetchrow(
            "SELECT session_id FROM signals WHERE id = $1", signal_id
        )

        if not row:
            raise HTTPException(status_code=404, detail="Signal not found")

        await conn.execute(
            """
            INSERT INTO signal_reactions (signal_id, user_id, reaction)
            VALUES ($1, $2, $3)
            ON CONFLICT (signal_id, user_id) DO UPDATE SET reaction = EXCLUDED.reaction 
            """,
            signal_id, reaction.user_id, reaction.reaction,
        )

        # recompute reaction counts
        reaction_rows = await conn.fetch(
            """
            SELECT reaction, COUNT(*) AS cnt
            FROM signal_reactions
            WHERE signal_id = $1
            GROUP BY reaction
            """,
            signal_id,
        )

        reactions = {r["reaction"]: r["cnt"] for r in reaction_rows}

        await conn.execute(
            "UPDATE signals SET reactions = $1 WHERE id = $2",
            reactions,  # This will be stored as JSONB
            signal_id
        )

        await manager.broadcast_to_session(
            row["session_id"],
            {
                "type": "reaction",
                "signal_id": signal_id,
                "reactions": reactions,
                "user_id": reaction.user_id,
                "reaction": reaction.reaction,
            },
        )

        return {"signal_id": signal_id, "reactions": reactions}
    finally:
        await release_db(conn)

@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(signal_id: str):
    conn = await get_db()

    try:
        return await _get_signal(conn, signal_id)
    finally:
        await release_db(conn)