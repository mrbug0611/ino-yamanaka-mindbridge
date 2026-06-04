"""Web Socket router for real time mind-link sessions"""
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.ConnectionManager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


async def _handle_message(session_id, user_id, msg):
    msg_type = msg.get('type')

    if msg_type == 'ping':
        await manager.send_to_user(session_id, user_id, {"type": "pong"})

    elif msg_type == 'typing':
        await manager.broadcast_to_session(
            session_id,
            {
                "type": "typing",
                "user_id": user_id,
                "is_typing": msg.get("is_typing", True),
            },
            exclude_user=user_id,
        )

    elif msg_type == "presence":

        # User reports their status

        await manager.broadcast_to_session(

            session_id,

            {

                "type": "presence",

                "user_id": user_id,

                "status": msg.get("status", "active"),

            },

            exclude_user=user_id,

        )


@router.websocket("/session/{session_id}/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: str,
):
    await manager.connect(websocket, session_id, user_id)

    # notify that other users joined
    online_users = manager.get_online_users(session_id)
    await manager.broadcast_to_session(
        session_id,
        {
            "type": "user_joined",
            "user_id": user_id,
            "online_users": online_users,
            "count": len(online_users),
        },
        exclude_user=user_id,
    )

    # Send welcome to the joining user
    await manager.send_to_user(
        session_id,
        user_id,
        {
            "type": "connected",
            "session_id": session_id,
            "online_users": online_users,
        },
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                await _handle_message(session_id, user_id, msg)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from {user_id}: {raw[:100]}")
            except Exception as e:
                logger.error(f"Error handling WS message: {e}")
    except WebSocketDisconnect:
        await manager.disconnect(session_id, user_id)
        online_users = manager.get_online_users(session_id)
        await manager.broadcast_to_session(
            session_id,
            {
                "type": "user_left",
                "user_id": user_id,
                "online_users": online_users,
                "count": len(online_users),
            },
        )
