"""

Pydantic models for MindBridge API

"""
import uuid
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


def gen_id() -> str:
    return str(uuid.uuid4()) # value used for unique identifiers

#── User Models ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel): # core data block for data validation and parsing in python
    username: str = Field(..., min_length=2, max_length=32)
    display_name: str = Field(..., min_length=1, max_length=64)
    skills: List[str] = Field(default_factory=list)
    avatar_color: str = "#7C3AED"


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    skills: List[str]
    avatar_color: str
    created_at: str
    last_active: str


# ─── Session Models ────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None # specify data types without enforcing them at runtime can be string or none
    host_id: str
    topic: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    host_id: str
    status: str
    topic: Optional[str]
    urgency_level: str
    created_at: str
    ended_at: Optional[str]
    summary: Optional[Dict[str, Any]]
    member_count: int = 0
    members: List[Dict[str, Any]] = Field(default_factory=list)


class SessionSummary(BaseModel):
    key_points: List[str]
    unresolved_questions: List[str]
    action_items: List[Dict[str, str]]
    next_steps: List[str]
    topic_clusters: List[Dict[str, Any]]


# ─── Signal Models ─────────────────────────────────────────────────────────────

class SignalCreate(BaseModel):
    session_id: str
    sender_id: str
    content: str = Field(..., min_length=1, max_length=4096)
    signal_type: str = "thought"
    parent_id: Optional[str] = None


class SignalResponse(BaseModel):
    id: str
    session_id: str
    sender_id: str
    sender_name: str
    sender_color: str
    content: str
    signal_type: str
    topic: Optional[str]
    urgency: str
    routed_to: List[str]
    reactions: Dict[str, int]
    parent_id: Optional[str]
    created_at: str


class ReactionAdd(BaseModel):
    user_id: str
    reaction: str = Field(..., pattern="^(⚡|💡|❓|✅|🔥|👁️)$")


# ─── WebSocket Messages ────────────────────────────────────────────────────────

class WSMessage(BaseModel):
    type: str
    payload: Dict[str, Any]
    sender_id: Optional[str] = None
    session_id: Optional[str] = None


class WSSignalBroadcast(BaseModel):
    type: str = "signal"
    signal: Dict[str, Any]
    routing: List[str]
    urgency: str


# ─── NLP Models ───────────────────────────────────────────────────────────────

class ClassificationResult(BaseModel):
    topic: str
    urgency: str
    signal_type: str
    routed_to: List[str]
    confidence: float


class RoutingRequest(BaseModel):
    content: str
    session_id: str
    sender_id: str
    available_users: List[Dict[str, Any]]