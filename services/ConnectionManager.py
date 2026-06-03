"""

Web Socket Connection Manager
Handles real-time mind-link sessions with pub/sub routing

"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # session id -> {user id -> web socket}
        self._sessions: Dict[str, Dict[str, WebSocket]] = {}

        # user id -> session id (reverse look up)
        self._user_sessions: Dict[str, str] = {}
        self._lock = asyncio.Lock() # thread locking

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
    ) -> None:
        await websocket.accept() # accept client requests
        async with self._lock: # acquire and automatically release asynchronous locks
            if session_id not in self._sessions:
                self._sessions[session_id] = {}
            self._sessions[session_id][user_id] = websocket
            self._user_sessions[user_id] = session_id
        logger.info(f"User {user_id} linked to session {session_id}")

    async def disconnect(self, session_id: str, user_id: str) -> None:
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].pop(user_id, None)
                if not self._sessions[session_id]:
                    del self._sessions[session_id]
            self._user_sessions.pop(user_id, None)
        logger.info(f"User {user_id} disconnected from session {session_id}")


    async def broadcast_to_session(
            self,
            session_id: str,
            message: Dict[str, Any],
            exclude_user: Optional[str] = None,
    ) -> None:
        """Send message to all members of a session."""

        if session_id not in self._sessions:
            return

        dead: list[str] = []
        payload = json.dumps(message)

        for user_id, ws in self._sessions[session_id].items():
            if user_id == exclude_user:
                continue

            try:
                await ws.send_text(payload)
            except Exception as e:
                logger.warning(f"Dead connection for {user_id}: {e}")
                dead.append(user_id)

        for user_id in dead:
            await self.disconnect(session_id, user_id)

    async def send_to_user(
        self,
        session_id: str,
        user_id: str,
        message: Dict[str, Any],
    ) -> bool:
        """Send message to a specific user in a session."""

        if session_id not in self._sessions:
            return False

        ws = self._sessions[session_id].get(user_id)
        payload = json.dumps(message)

        if not ws:
            return False

        try:
            await ws.send_text(payload)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to {user_id}: {e}")
            await self.disconnect(session_id, user_id)
            return False

    async def broadcast_to_routed(
        self,
        session_id: str,
        routed_to: list[str],
        message: Dict[str, Any],
        sender_id: Optional[str] = None,
    ) -> None:
        """
        Send to routed users; also send sender a 'sent' confirmation.
        Everyone else in the session gets a 'signal_shadow' (muted view).
        """

        payload_full = json.dumps(message)
        shadow_msg = {
            **message, # unpacks dictionary
            "type": "signal_shadow",
            "dimmed": True,
        }

        payload_shadow = json.dumps(shadow_msg)

        if session_id not in self._sessions:
            return

        dead = []

        for user_id, ws in self._sessions[session_id].items():
            try:
                if user_id in routed_to or user_id == sender_id:
                    await ws.send_text(payload_full)
                else:
                    await ws.send_text(payload_shadow)

            except (WebSocketDisconnect, ConnectionError, RuntimeError):
                dead.append(user_id)

        for uid in dead:
            await self.disconnect(session_id, uid)

    def get_online_users(self, session_id: str) -> list[str]:
        """Return a list of users who are currently online via user_id."""
        return list(self._sessions.get(session_id, {}).keys())

    def session_count(self, session_id: str) -> int:
        return len(self._sessions.get(session_id, {}))

    def total_connections(self) -> int:
        return sum(len(v) for v in self._sessions.values())

#singleton
manager = ConnectionManager()










