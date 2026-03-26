"""Data collection — tracks usage patterns anonymously for insights."""

import json
import logging
import time

import aiosqlite

from backend.db.database import DB_PATH, _is_postgres

logger = logging.getLogger(__name__)


async def log_preference(prefs: dict):
    """Log anonymized preference snapshot."""
    try:
        if _is_postgres():
            from backend.db.database import _pg_get_pool
            pool = await _pg_get_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO preference_log (household_size, num_dinners, has_children,
                        dietary_restrictions, lifestyle_preferences, budget_per_week)
                    VALUES ($1,$2,$3,$4,$5,$6)
                """, prefs.get("household_size"), prefs.get("num_dinners"),
                     prefs.get("has_children", False),
                     json.dumps(prefs.get("dietary_restrictions", [])),
                     json.dumps(prefs.get("lifestyle_preferences", [])),
                     prefs.get("budget_per_week"))
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    """INSERT INTO preference_log (household_size, num_dinners, has_children,
                        dietary_restrictions, lifestyle_preferences, budget_per_week)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (prefs.get("household_size"), prefs.get("num_dinners"),
                     prefs.get("has_children", False),
                     json.dumps(prefs.get("dietary_restrictions", [])),
                     json.dumps(prefs.get("lifestyle_preferences", [])),
                     prefs.get("budget_per_week")))
                await db.commit()
    except Exception as e:
        logger.debug(f"preference_log: {e}")


async def log_generation(menu_id: str, ai_provider: str, recipe_count: int,
                         total_cost: float, total_savings: float,
                         offer_count: int, duration_ms: int):
    """Log menu generation metadata."""
    try:
        if _is_postgres():
            from backend.db.database import _pg_get_pool
            pool = await _pg_get_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO generation_log (menu_id, ai_provider, recipe_count,
                        total_cost, total_savings, offer_count, generation_time_ms)
                    VALUES ($1,$2,$3,$4,$5,$6,$7)
                """, menu_id, ai_provider, recipe_count, total_cost, total_savings,
                     offer_count, duration_ms)
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    """INSERT INTO generation_log (menu_id, ai_provider, recipe_count,
                        total_cost, total_savings, offer_count, generation_time_ms)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (menu_id, ai_provider, recipe_count, total_cost, total_savings,
                     offer_count, duration_ms))
                await db.commit()
    except Exception as e:
        logger.debug(f"generation_log: {e}")


async def log_swap(old_id: str, old_title: str, new_id: str, new_title: str,
                   day: str, reason: str):
    """Log recipe swap."""
    try:
        if _is_postgres():
            from backend.db.database import _pg_get_pool
            pool = await _pg_get_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO swap_log (old_recipe_id, old_recipe_title, new_recipe_id,
                        new_recipe_title, day, reason) VALUES ($1,$2,$3,$4,$5,$6)
                """, old_id, old_title, new_id, new_title, day, reason)
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    """INSERT INTO swap_log (old_recipe_id, old_recipe_title, new_recipe_id,
                        new_recipe_title, day, reason) VALUES (?, ?, ?, ?, ?, ?)""",
                    (old_id, old_title, new_id, new_title, day, reason))
                await db.commit()
    except Exception as e:
        logger.debug(f"swap_log: {e}")


async def update_recipe_stats(recipe_id: str, event: str):
    """Increment recipe stat counter. event: 'selected', 'swapped_away', 'liked', 'disliked'"""
    col_map = {
        'selected': 'times_selected',
        'swapped_away': 'times_swapped_away',
        'liked': 'times_liked',
        'disliked': 'times_disliked',
    }
    col = col_map.get(event)
    if not col:
        return
    try:
        if _is_postgres():
            from backend.db.database import _pg_get_pool
            pool = await _pg_get_pool()
            async with pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO recipe_stats (recipe_id, {col}, last_selected, updated_at)
                    VALUES ($1, 1, NOW(), NOW())
                    ON CONFLICT (recipe_id) DO UPDATE SET {col} = recipe_stats.{col} + 1, updated_at = NOW()
                """, recipe_id)
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(f"""
                    INSERT INTO recipe_stats (recipe_id, {col}) VALUES (?, 1)
                    ON CONFLICT (recipe_id) DO UPDATE SET {col} = {col} + 1
                """, (recipe_id,))
                await db.commit()
    except Exception as e:
        logger.debug(f"recipe_stats: {e}")
