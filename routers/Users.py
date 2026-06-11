"""

Users API Router

"""
import json

from fastapi import APIRouter, HTTPException, Query

from database import get_db, release_db
from models import UserCreate, UserResponse, gen_id

router = APIRouter()


def _row_to_user(row) -> UserResponse:
    skills = row["skills"]

    while isinstance(skills, str):
        try:
            parsed = json.loads(skills)

            if parsed == skills:
                break
            skills = parsed
        except json.JSONDecodeError:
            break

    if not isinstance(skills, list):
        skills  # noqa: B018

    return UserResponse(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"],
        skills=skills,
        avatar_color=row["avatar_color"],
        created_at=str(row["created_at"]),
        last_active=str(row["last_active"]),
    )


@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate):
    conn = await get_db()

    try:
        user_id = gen_id()

        try:
            row = await conn.fetchrow(
                """
                INSERT INTO users (id, username, display_name, skills, avatar_color)
                VALUES ($1, $2, $3, $4::jsonb, $5)
                RETURNING *
                """,
                user_id, user.username, user.display_name,
                json.dumps(user.skills), user.avatar_color,
            )

        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail="Username already taken") from e
            raise HTTPException(status_code=500, detail=str(e)) from e
        return _row_to_user(row)
    finally:
        await release_db(conn)

@router.get("/", response_model=list[UserResponse])
async def list_users(username: str | None = Query(None) ):
    conn = await get_db()

    try:
        if username:
            rows = await conn.fetch(
                "SELECT * FROM users WHERE username = $1 LIMIT 1",
                username,
            )

        else:
            rows = await conn.fetch(
                "SELECT * FROM users ORDER BY last_active DESC LIMIT 100"
            )

        return [_row_to_user(r) for r in rows]

    finally:
        await release_db(conn)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    conn = await get_db()

    try:
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return _row_to_user(row)
    finally:
        await release_db(conn)


