"""

Pydantic models for MindBridge API

"""
import uuid
from typing import Any

from pydantic import BaseModel, Field


def gen_id() -> str:
    return str(uuid.uuid4()) # value used for unique identifiers

#── User Models ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel): # core data block for data validation and parsing in python
    username: str = Field(..., min_length=2, max_length=32)
    display_name: str = Field(..., min_length=1, max_length=64)
    skills: list[str] = Field(default_factory=list)
    avatar_color: str = "#7C3AED"


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    skills: list[str]
    avatar_color: str
    created_at: str
    last_active: str


# ─── Session Models ────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    description: str | None = None # specify data types without enforcing them at runtime can be string or none
    host_id: str
    topic: str | None = None


class SessionResponse(BaseModel):
    id: str
    title: str
    description: str | None
    host_id: str
    status: str
    topic: str | None
    urgency_level: str
    created_at: str
    ended_at: str | None
    summary: dict[str, Any] | None
    member_count: int = 0
    members: list[dict[str, Any]] = Field(default_factory=list)


class SessionSummary(BaseModel):
    key_points: list[str]
    unresolved_questions: list[str]
    action_items: list[dict[str, str]]
    next_steps: list[str]
    topic_clusters: list[dict[str, Any]]


# ─── Signal Models ─────────────────────────────────────────────────────────────

class SignalCreate(BaseModel):
    session_id: str
    sender_id: str
    content: str = Field(..., min_length=1, max_length=4096)
    signal_type: str = "thought"
    parent_id: str | None = None

class SignalResponse(BaseModel):
    id: str
    session_id: str
    sender_id: str
    sender_name: str
    sender_color: str
    content: str
    signal_type: str
    topic: str | None
    urgency: str
    routed_to: list[str]
    reactions: dict[str, int]
    parent_id: str | None
    created_at: str


class ReactionAdd(BaseModel):
    user_id: str
    reaction: str = Field(..., pattern="^(⚡|💡|❓|✅|🔥|👁️)$")


# ─── WebSocket Messages ────────────────────────────────────────────────────────

class WSMessage(BaseModel):
    type: str
    payload: dict[str, Any]
    sender_id: str | None = None
    session_id: str | None = None


class WSSignalBroadcast(BaseModel):
    type: str = "signal"
    signal: dict[str, Any]
    routing: list[str]
    urgency: str


# ─── NLP Models ───────────────────────────────────────────────────────────────

class ClassificationResult(BaseModel):
    topic: str
    urgency: str
    signal_type: str
    routed_to: list[str]
    confidence: float


class RoutingRequest(BaseModel):
    content: str
    session_id: str
    sender_id: str
    available_users: list[dict[str, Any]]
