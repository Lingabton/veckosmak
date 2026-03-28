"""Magic link authentication — email-based, no passwords.

Extended with subscription tiers, profile management, and menu history.
"""

import hashlib
import json
import logging
import uuid
from datetime import date, datetime, timedelta

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


async def get_user_by_id(user_id: str) -> dict | None:
    """Get user by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
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


async def update_user_profile(email: str, name: str = None, bio: str = None,
                               city: str = None, is_public: bool = None):
    """Update user profile fields."""
    async with aiosqlite.connect(DB_PATH) as db:
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if bio is not None:
            updates.append("bio = ?")
            params.append(bio)
        if city is not None:
            updates.append("city = ?")
            params.append(city)
        if is_public is not None:
            updates.append("is_public = ?")
            params.append(is_public)
        if not updates:
            return
        params.append(email.lower())
        await db.execute(f"UPDATE users SET {', '.join(updates)} WHERE email = ?", params)
        await db.commit()


async def check_generation_limit(email: str) -> dict:
    """Check if user can generate a menu. Returns {allowed, remaining, tier, limit}."""
    from backend.config import get_settings
    settings = get_settings()

    user = await get_user(email) if email else None
    tier = user.get("subscription_tier", "free") if user else "free"

    # Check subscription expiry
    if tier != "free" and user:
        expires = user.get("subscription_expires")
        if expires:
            try:
                if datetime.fromisoformat(expires) < datetime.now():
                    tier = "free"
            except (ValueError, TypeError):
                pass

    limit = settings.premium_generations_per_day if tier != "free" else settings.free_generations_per_day
    today = date.today().isoformat()

    if not user:
        return {"allowed": True, "remaining": limit, "tier": "free", "limit": limit}

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await db.execute(
            "SELECT generations_today, generations_reset_date FROM users WHERE email = ?",
            (email.lower(),)
        )
        result = await row.fetchone()

        if not result:
            return {"allowed": True, "remaining": limit, "tier": tier, "limit": limit}

        reset_date = result["generations_reset_date"]
        count = result["generations_today"] or 0

        # Reset counter if new day
        if reset_date != today:
            await db.execute(
                "UPDATE users SET generations_today = 0, generations_reset_date = ? WHERE email = ?",
                (today, email.lower())
            )
            await db.commit()
            count = 0

        remaining = max(0, limit - count)
        return {"allowed": remaining > 0, "remaining": remaining, "tier": tier, "limit": limit}


async def increment_generation_count(email: str):
    """Increment the daily generation counter for a user."""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users SET
                generations_today = CASE WHEN generations_reset_date = ? THEN generations_today + 1 ELSE 1 END,
                generations_reset_date = ?
               WHERE email = ?""",
            (today, today, email.lower())
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


async def get_user_menu_history(email: str, limit: int = 20) -> list[dict]:
    """Get user's menu history."""
    user_id = hashlib.md5(email.lower().encode()).hexdigest()[:12]
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute(
            "SELECT * FROM user_menus WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        results = []
        async for row in rows:
            r = dict(row)
            r["menu_data"] = json.loads(r["menu_data"]) if r.get("menu_data") else None
            results.append(r)
        return results


async def set_subscription(email: str, tier: str, months: int = 1):
    """Set user subscription tier."""
    expires = datetime.now() + timedelta(days=30 * months)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET subscription_tier = ?, subscription_expires = ? WHERE email = ?",
            (tier, expires.isoformat(), email.lower())
        )
        await db.commit()
