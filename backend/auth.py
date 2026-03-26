"""Magic link authentication — email-based, no passwords."""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta

import aiosqlite

from backend.db.database import DB_PATH

logger = logging.getLogger(__name__)

TOKEN_EXPIRY_MINUTES = 15


async def create_magic_link(email: str) -> str:
    """Create a magic link token for the given email.
    Returns the token (to be sent via email)."""
    token = uuid.uuid4().hex
    expires = datetime.now() + timedelta(minutes=TOKEN_EXPIRY_MINUTES)

    async with aiosqlite.connect(DB_PATH) as db:
        # Invalidate old tokens for this email
        await db.execute(
            "UPDATE auth_tokens SET used = TRUE WHERE email = ? AND used = FALSE",
            (email.lower(),)
        )
        await db.execute(
            "INSERT INTO auth_tokens (token, email, expires_at) VALUES (?, ?, ?)",
            (token, email.lower(), expires.isoformat())
        )
        await db.commit()

    return token


async def verify_token(token: str) -> str | None:
    """Verify a magic link token. Returns email if valid, None if not."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await db.execute(
            "SELECT * FROM auth_tokens WHERE token = ? AND used = FALSE",
            (token,)
        )
        result = await row.fetchone()

        if not result:
            return None

        if datetime.fromisoformat(result["expires_at"]) < datetime.now():
            return None

        # Mark as used
        await db.execute("UPDATE auth_tokens SET used = TRUE WHERE token = ?", (token,))

        # Create or update user
        email = result["email"]
        user_id = hashlib.md5(email.encode()).hexdigest()[:12]
        await db.execute(
            """INSERT INTO users (id, email, last_login) VALUES (?, ?, ?)
               ON CONFLICT(email) DO UPDATE SET last_login = ?""",
            (user_id, email, datetime.now().isoformat(), datetime.now().isoformat())
        )
        await db.commit()

        return email


async def get_user(email: str) -> dict | None:
    """Get user by email."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await db.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        result = await row.fetchone()
        if result:
            r = dict(result)
            r["preferences"] = json.loads(r["preferences"]) if r.get("preferences") else None
            return r
        return None


async def save_user_preferences(email: str, preferences: dict):
    """Save user preferences to DB."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET preferences = ? WHERE email = ?",
            (json.dumps(preferences), email.lower())
        )
        await db.commit()


async def save_user_menu(email: str, menu_data: dict):
    """Save a generated menu to user history."""
    user_id = hashlib.md5(email.lower().encode()).hexdigest()[:12]
    menu_id = uuid.uuid4().hex[:8]
    now = datetime.now()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO user_menus (id, user_id, week_number, year, menu_data) VALUES (?, ?, ?, ?, ?)",
            (menu_id, user_id, now.isocalendar()[1], now.year, json.dumps(menu_data))
        )
        await db.commit()
