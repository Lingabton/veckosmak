import aiosqlite
import json
from pathlib import Path
from typing import Optional

from backend.models.offer import Offer
from backend.models.recipe import Recipe

DB_PATH = Path("veckosmak.db")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    schema = SCHEMA_PATH.read_text()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(schema)
        # Migrate: add rating columns if missing
        for col in ["rating REAL", "rating_count INTEGER", "nutrition TEXT", "cooking_method TEXT"]:
            try:
                await db.execute(f"ALTER TABLE recipes ADD COLUMN {col}")
            except Exception:
                pass
        # Seed default store
        await db.execute(
            """INSERT OR IGNORE INTO stores (id, name, city, url, scraper_class)
               VALUES (?, ?, ?, ?, ?)""",
            (
                "ica-maxi-1004097",
                "Maxi ICA Stormarknad Orebro Boglundsangen",
                "Orebro",
                "https://www.ica.se/erbjudanden/maxi-ica-stormarknad-orebro-boglundsangen-1004097/",
                "IcaMaxiScraper",
            ),
        )
        await db.commit()


async def save_offers(offers: list[Offer]):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        for offer in offers:
            await db.execute(
                """INSERT OR REPLACE INTO offers
                   (id, store_id, product_name, brand, category, offer_price,
                    original_price, unit, quantity_deal, max_per_household,
                    valid_from, valid_to, requires_membership, image_url, raw_text)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    offer.id,
                    offer.store_id,
                    offer.product_name,
                    offer.brand,
                    offer.category,
                    offer.offer_price,
                    offer.original_price,
                    offer.unit,
                    offer.quantity_deal,
                    offer.max_per_household,
                    offer.valid_from.isoformat(),
                    offer.valid_to.isoformat(),
                    offer.requires_membership,
                    offer.image_url,
                    offer.raw_text,
                ),
            )
        await db.commit()


async def save_recipes(recipes: list[Recipe]):
    async with aiosqlite.connect(DB_PATH) as db:
        for recipe in recipes:
            await db.execute(
                """INSERT OR REPLACE INTO recipes
                   (id, title, source_url, source, servings, cook_time_minutes,
                    difficulty, tags, diet_labels, ingredients, instructions,
                    image_url, rating, rating_count, nutrition, cooking_method)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    recipe.id,
                    recipe.title,
                    recipe.source_url,
                    recipe.source,
                    recipe.servings,
                    recipe.cook_time_minutes,
                    recipe.difficulty,
                    json.dumps(recipe.tags),
                    json.dumps(recipe.diet_labels),
                    json.dumps([i.model_dump() for i in recipe.ingredients]),
                    json.dumps(recipe.instructions),
                    recipe.image_url,
                    recipe.rating,
                    recipe.rating_count,
                    json.dumps(recipe.nutrition.model_dump() if recipe.nutrition else None),
                    recipe.cooking_method,
                ),
            )
        await db.commit()


async def get_all_recipes() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute("SELECT * FROM recipes")
        results = []
        async for row in rows:
            r = dict(row)
            r["tags"] = json.loads(r["tags"]) if r["tags"] else []
            r["diet_labels"] = json.loads(r["diet_labels"]) if r["diet_labels"] else []
            r["ingredients"] = json.loads(r["ingredients"]) if r["ingredients"] else []
            r["instructions"] = json.loads(r["instructions"]) if r["instructions"] else []
            results.append(r)
        return results


async def get_current_offers(store_id: str, category: Optional[str] = None) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM offers WHERE store_id = ? AND valid_to >= date('now')"
        params: list = [store_id]
        if category:
            categories = [c.strip() for c in category.split(",")]
            placeholders = ",".join("?" * len(categories))
            query += f" AND category IN ({placeholders})"
            params.extend(categories)
        rows = await db.execute(query, params)
        return [dict(row) async for row in rows]
