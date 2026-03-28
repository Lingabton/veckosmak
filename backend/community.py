"""Community features — shared menus, recipe ratings, favorites."""

import json
import logging
import uuid

import aiosqlite

from backend.db.database import DB_PATH

logger = logging.getLogger(__name__)


async def share_menu(
    user_id: str,
    title: str,
    description: str,
    menu_data: dict,
    store_name: str,
    city: str,
    total_cost: float,
    total_savings: float,
    num_meals: int,
    dietary_tags: list[str],
) -> str:
    """Share a menu with the community. Returns the shared menu ID."""
    menu_id = uuid.uuid4().hex[:10]
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO shared_menus
                   (id, user_id, title, description, menu_data, store_name, city,
                    total_cost, total_savings, num_meals, dietary_tags, likes, views,
                    is_featured, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, CURRENT_TIMESTAMP)""",
                (
                    menu_id,
                    user_id,
                    title,
                    description,
                    json.dumps(menu_data),
                    store_name,
                    city,
                    total_cost,
                    total_savings,
                    num_meals,
                    json.dumps(dietary_tags),
                ),
            )
            await db.commit()
        logger.info("Menu %s shared by user %s", menu_id, user_id)
    except Exception as e:
        logger.error("Failed to share menu: %s", e)
        raise
    return menu_id


def _row_to_menu(row: aiosqlite.Row, columns: list[str]) -> dict:
    """Convert a database row to a menu dict."""
    menu = dict(zip(columns, row))
    if menu.get("menu_data"):
        menu["menu_data"] = json.loads(menu["menu_data"])
    if menu.get("dietary_tags"):
        menu["dietary_tags"] = json.loads(menu["dietary_tags"])
    return menu


async def get_shared_menu(menu_id: str) -> dict | None:
    """Get a shared menu by ID and increment its view count."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE shared_menus SET views = views + 1 WHERE id = ?",
                (menu_id,),
            )
            await db.commit()

            cursor = await db.execute(
                "SELECT * FROM shared_menus WHERE id = ?", (menu_id,)
            )
            columns = [desc[0] for desc in cursor.description]
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_menu(row, columns)
    except Exception as e:
        logger.error("Failed to get shared menu %s: %s", menu_id, e)
        raise


async def get_popular_menus(limit: int = 10, city: str | None = None) -> list[dict]:
    """Get top menus ordered by likes, optionally filtered by city."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            if city:
                cursor = await db.execute(
                    """SELECT * FROM shared_menus
                       WHERE city = ?
                       ORDER BY likes DESC
                       LIMIT ?""",
                    (city, limit),
                )
            else:
                cursor = await db.execute(
                    """SELECT * FROM shared_menus
                       ORDER BY likes DESC
                       LIMIT ?""",
                    (limit,),
                )
            columns = [desc[0] for desc in cursor.description]
            rows = await cursor.fetchall()
            return [_row_to_menu(row, columns) for row in rows]
    except Exception as e:
        logger.error("Failed to get popular menus: %s", e)
        raise


async def get_recent_menus(limit: int = 10, city: str | None = None) -> list[dict]:
    """Get the most recently shared menus."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            if city:
                cursor = await db.execute(
                    """SELECT * FROM shared_menus
                       WHERE city = ?
                       ORDER BY created_at DESC
                       LIMIT ?""",
                    (city, limit),
                )
            else:
                cursor = await db.execute(
                    """SELECT * FROM shared_menus
                       ORDER BY created_at DESC
                       LIMIT ?""",
                    (limit,),
                )
            columns = [desc[0] for desc in cursor.description]
            rows = await cursor.fetchall()
            return [_row_to_menu(row, columns) for row in rows]
    except Exception as e:
        logger.error("Failed to get recent menus: %s", e)
        raise


async def get_user_shared_menus(user_id: str) -> list[dict]:
    """Get all menus shared by a specific user."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """SELECT * FROM shared_menus
                   WHERE user_id = ?
                   ORDER BY created_at DESC""",
                (user_id,),
            )
            columns = [desc[0] for desc in cursor.description]
            rows = await cursor.fetchall()
            return [_row_to_menu(row, columns) for row in rows]
    except Exception as e:
        logger.error("Failed to get menus for user %s: %s", user_id, e)
        raise


async def toggle_like(user_id: str, menu_id: str) -> dict:
    """Toggle a like on a shared menu. Returns liked state and total likes."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT 1 FROM community_likes WHERE user_id = ? AND menu_id = ?",
                (user_id, menu_id),
            )
            existing = await cursor.fetchone()

            if existing:
                await db.execute(
                    "DELETE FROM community_likes WHERE user_id = ? AND menu_id = ?",
                    (user_id, menu_id),
                )
                await db.execute(
                    "UPDATE shared_menus SET likes = likes - 1 WHERE id = ?",
                    (menu_id,),
                )
                liked = False
            else:
                await db.execute(
                    """INSERT INTO community_likes (user_id, menu_id, created_at)
                       VALUES (?, ?, CURRENT_TIMESTAMP)""",
                    (user_id, menu_id),
                )
                await db.execute(
                    "UPDATE shared_menus SET likes = likes + 1 WHERE id = ?",
                    (menu_id,),
                )
                liked = True

            await db.commit()

            cursor = await db.execute(
                "SELECT likes FROM shared_menus WHERE id = ?", (menu_id,)
            )
            row = await cursor.fetchone()
            total_likes = row[0] if row else 0

        logger.info(
            "User %s %s menu %s", user_id, "liked" if liked else "unliked", menu_id
        )
        return {"liked": liked, "total_likes": total_likes}
    except Exception as e:
        logger.error("Failed to toggle like for menu %s: %s", menu_id, e)
        raise


async def rate_recipe(
    user_id: str, recipe_id: str, rating: int, comment: str | None = None
) -> None:
    """Rate a recipe (1-5). Upserts if user already rated this recipe."""
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO recipe_ratings (user_id, recipe_id, rating, comment, created_at)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(user_id, recipe_id)
                   DO UPDATE SET rating = excluded.rating,
                                 comment = excluded.comment,
                                 created_at = CURRENT_TIMESTAMP""",
                (user_id, recipe_id, rating, comment),
            )
            await db.commit()
        logger.info("User %s rated recipe %s: %d", user_id, recipe_id, rating)
    except Exception as e:
        logger.error("Failed to rate recipe %s: %s", recipe_id, e)
        raise


async def get_recipe_ratings(recipe_id: str) -> dict:
    """Get aggregate ratings and recent reviews for a recipe."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Average and count
            cursor = await db.execute(
                """SELECT AVG(rating), COUNT(*)
                   FROM recipe_ratings WHERE recipe_id = ?""",
                (recipe_id,),
            )
            row = await cursor.fetchone()
            average = round(row[0], 1) if row[0] is not None else 0.0
            count = row[1]

            # Distribution
            cursor = await db.execute(
                """SELECT rating, COUNT(*)
                   FROM recipe_ratings
                   WHERE recipe_id = ?
                   GROUP BY rating""",
                (recipe_id,),
            )
            dist_rows = await cursor.fetchall()
            distribution = {i: 0 for i in range(1, 6)}
            for r, c in dist_rows:
                distribution[r] = c

            # Recent reviews
            cursor = await db.execute(
                """SELECT user_id, rating, comment, created_at
                   FROM recipe_ratings
                   WHERE recipe_id = ?
                   ORDER BY created_at DESC
                   LIMIT 10""",
                (recipe_id,),
            )
            recent = [
                {
                    "user_id": r[0],
                    "rating": r[1],
                    "comment": r[2],
                    "created_at": r[3],
                }
                for r in await cursor.fetchall()
            ]

        return {
            "average": average,
            "count": count,
            "distribution": distribution,
            "recent": recent,
        }
    except Exception as e:
        logger.error("Failed to get ratings for recipe %s: %s", recipe_id, e)
        raise


async def toggle_favorite(user_id: str, recipe_id: str) -> bool:
    """Toggle a recipe as favorite. Returns the new favorite state."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT 1 FROM user_favorites WHERE user_id = ? AND recipe_id = ?",
                (user_id, recipe_id),
            )
            existing = await cursor.fetchone()

            if existing:
                await db.execute(
                    "DELETE FROM user_favorites WHERE user_id = ? AND recipe_id = ?",
                    (user_id, recipe_id),
                )
                favorited = False
            else:
                await db.execute(
                    """INSERT INTO user_favorites (user_id, recipe_id, created_at)
                       VALUES (?, ?, CURRENT_TIMESTAMP)""",
                    (user_id, recipe_id),
                )
                favorited = True

            await db.commit()

        logger.info(
            "User %s %s recipe %s",
            user_id,
            "favorited" if favorited else "unfavorited",
            recipe_id,
        )
        return favorited
    except Exception as e:
        logger.error("Failed to toggle favorite for recipe %s: %s", recipe_id, e)
        raise


async def get_user_favorites(user_id: str) -> list[str]:
    """Get the list of favorite recipe IDs for a user."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """SELECT recipe_id FROM user_favorites
                   WHERE user_id = ?
                   ORDER BY created_at DESC""",
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    except Exception as e:
        logger.error("Failed to get favorites for user %s: %s", user_id, e)
        raise


async def get_community_stats() -> dict:
    """Get aggregate community statistics."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM shared_menus")
            total_shared_menus = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT COUNT(*) FROM recipe_ratings")
            total_ratings = (await cursor.fetchone())[0]

            cursor = await db.execute(
                """SELECT COUNT(DISTINCT user_id) FROM (
                       SELECT user_id FROM shared_menus
                       UNION
                       SELECT user_id FROM recipe_ratings
                       UNION
                       SELECT user_id FROM community_likes
                   )"""
            )
            total_users = (await cursor.fetchone())[0]

            cursor = await db.execute(
                """SELECT city, COUNT(*) as cnt
                   FROM shared_menus
                   WHERE city IS NOT NULL
                   GROUP BY city
                   ORDER BY cnt DESC
                   LIMIT 1"""
            )
            row = await cursor.fetchone()
            popular_city = row[0] if row else None

        return {
            "total_shared_menus": total_shared_menus,
            "total_ratings": total_ratings,
            "total_users": total_users,
            "popular_city": popular_city,
        }
    except Exception as e:
        logger.error("Failed to get community stats: %s", e)
        raise
