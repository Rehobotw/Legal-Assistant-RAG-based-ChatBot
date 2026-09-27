"""Persistent chat session store.

Saves session_id -> list of {role, content, timestamp, extra} to JSON
so sessions survive server reloads and restarts, displayed in the frontend sidebar.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import BACKEND_DIR

SESSIONS_FILE = BACKEND_DIR / "data" / "chat_sessions.json"
_sessions: dict[str, dict[str, Any]] = {}


def _load_sessions() -> None:
    global _sessions
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                _sessions = json.load(f)
        except Exception as e:
            print(f"Error loading chat sessions: {e}")
            _sessions = {}


def _save_sessions() -> None:
    try:
        SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(_sessions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving chat sessions: {e}")


# Load sessions on module import
_load_sessions()


def create_session() -> str:
    session_id = uuid.uuid4().hex[:12]
    create_session_with_id(session_id)
    return session_id


def create_session_with_id(session_id: str) -> None:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "id": session_id,
            "title": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
        }
        _save_sessions()


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

    _save_sessions()


def get_session(session_id: str) -> dict[str, Any] | None:
    return _sessions.get(session_id)


def list_sessions() -> list[dict[str, Any]]:
    """Return all non-empty sessions sorted newest-first for the sidebar."""
    result = []
    for sid, data in _sessions.items():
        if data.get("messages"):
            result.append({
                "id": sid,
                "title": data.get("title") or "New Inquiry",
                "created_at": data.get("created_at") or datetime.now(timezone.utc).isoformat(),
                "message_count": len(data["messages"]),
            })
    result.sort(key=lambda s: s["created_at"], reverse=True)
    return result


def delete_session(session_id: str) -> bool:
    if session_id in _sessions:
        del _sessions[session_id]
        _save_sessions()
        return True
    return False

