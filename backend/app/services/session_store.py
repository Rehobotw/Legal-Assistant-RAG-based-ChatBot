"""In-memory chat session store.

Keeps a simple dict of session_id → list of {role, content, timestamp}
so the frontend can fetch real history grouped by Today / Yesterday / Previous.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


_sessions: dict[str, dict[str, Any]] = {}


def create_session() -> str:
    session_id = uuid.uuid4().hex[:12]
    _sessions[session_id] = {
        "id": session_id,
        "title": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "messages": [],
    }
    return session_id


def add_message(session_id: str, role: str, content: str, extra: dict | None = None) -> None:
    if session_id not in _sessions:
        create_session_with_id(session_id)
    msg: dict[str, Any] = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        msg.update(extra)
    _sessions[session_id]["messages"].append(msg)
    # Auto-title from first user message
    if role == "user" and not _sessions[session_id]["title"]:
        _sessions[session_id]["title"] = content[:80]


def create_session_with_id(session_id: str) -> None:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "id": session_id,
            "title": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
        }


def get_session(session_id: str) -> dict[str, Any] | None:
    return _sessions.get(session_id)


def list_sessions() -> list[dict[str, Any]]:
    """Return all sessions sorted newest-first, without full message bodies."""
    result = []
    for sid, data in _sessions.items():
        result.append({
            "id": sid,
            "title": data["title"],
            "created_at": data["created_at"],
            "message_count": len(data["messages"]),
        })
    result.sort(key=lambda s: s["created_at"], reverse=True)
    return result
