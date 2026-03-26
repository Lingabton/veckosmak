"""Database layer — supports SQLite (dev) and PostgreSQL (prod).

Set DATABASE_URL env var:
  SQLite:    sqlite:///./veckosmak.db  (default)
  Postgres:  postgresql://user:pass@host/db
"""

import json
import logging
from pathlib import Path
from typing import Optional

from backend.config import get_settings
from backend.models.offer import Offer
from backend.models.recipe import Recipe

logger = logging.getLogger(__name__)

DB_PATH = Path("veckosmak.db")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Detect database type from URL
def _is_postgres():
    return get_settings().database_url.startswith("postgresql") and not _force_sqlite


# --- SQLite implementation ---

async def _sqlite_connect():
    import aiosqlite
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


_force_sqlite = False

async def init_db():
    global _force_sqlite
    if _is_postgres() and not _force_sqlite:
        try:
            await _pg_init()
            logger.info("PostgreSQL connected successfully")
        except Exception as e:
            logger.error(f"PostgreSQL failed — falling back to SQLite: {e}")
            _force_sqlite = True
            await _sqlite_init()
    else:
        await _sqlite_init()


async def _sqlite_init():
    import aiosqlite
    schema = SCHEMA_PATH.read_text()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(schema)
        for col in ["rating REAL", "rating_count INTEGER", "nutrition TEXT", "cooking_method TEXT"]:
            try:
                await db.execute(f"ALTER TABLE recipes ADD COLUMN {col}")
            except Exception:
                pass
        await db.execute(
            """INSERT OR IGNORE INTO stores (id, name, city, url, scraper_class)
               VALUES (?, ?, ?, ?, ?)""",
            ("ica-maxi-1004097", "Maxi ICA Stormarknad Orebro Boglundsangen",
             "Orebro", "https://www.ica.se/erbjudanden/maxi-ica-stormarknad-orebro-boglundsangen-1004097/",
             "IcaMaxiScraper"),
        )
        await db.commit()


# --- PostgreSQL implementation ---

_pg_pool = None

async def _pg_get_pool():
    global _pg_pool
    if _pg_pool is None:
        import asyncpg
        import ssl as _ssl
        dsn = get_settings().database_url
        # Remove unsupported params
        dsn = dsn.replace("&channel_binding=require", "").replace("?channel_binding=require&", "?")
        dsn = dsn.replace("?channel_binding=require", "")
        # Also handle sslmode in DSN — asyncpg uses ssl parameter instead
        if "sslmode=require" in dsn:
            dsn = dsn.replace("?sslmode=require&", "?").replace("&sslmode=require", "").replace("?sslmode=require", "")
        if dsn.endswith("?") or dsn.endswith("&"):
            dsn = dsn.rstrip("?&")

        ssl_ctx = _ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = _ssl.CERT_NONE

        logger.info(f"Connecting to PostgreSQL: {dsn[:50]}...")
        _pg_pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5, ssl=ssl_ctx)
        logger.info("PostgreSQL pool created")
    return _pg_pool


async def _pg_init():
    pool = await _pg_get_pool()
    async with pool.acquire() as conn:
        # Create tables (PostgreSQL syntax)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS stores (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, city TEXT, url TEXT,
                scraper_class TEXT, created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS offers (
                id TEXT PRIMARY KEY, store_id TEXT REFERENCES stores(id),
                product_name TEXT NOT NULL, brand TEXT, category TEXT NOT NULL,
                offer_price REAL NOT NULL, original_price REAL, unit TEXT,
                quantity_deal TEXT, max_per_household INTEGER,
                valid_from DATE NOT NULL, valid_to DATE NOT NULL,
                requires_membership BOOLEAN DEFAULT FALSE, image_url TEXT,
                raw_text TEXT, scraped_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS recipes (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, source_url TEXT,
                source TEXT NOT NULL, servings INTEGER, cook_time_minutes INTEGER,
                difficulty TEXT, tags TEXT, diet_labels TEXT,
                ingredients TEXT NOT NULL, instructions TEXT NOT NULL,
                image_url TEXT, rating REAL, rating_count INTEGER,
                nutrition TEXT, cooking_method TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT,
                preferences TEXT, created_at TIMESTAMP DEFAULT NOW(), last_login TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY, email TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL, used BOOLEAN DEFAULT FALSE
            );
            CREATE TABLE IF NOT EXISTS user_menus (
                id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id),
                week_number INTEGER, year INTEGER, menu_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS generated_menus (
                id TEXT PRIMARY KEY, store_id TEXT, week_number INTEGER, year INTEGER,
                preferences TEXT NOT NULL, menu_data TEXT NOT NULL,
                total_cost REAL, total_savings REAL, created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS price_history (
                id SERIAL PRIMARY KEY, store_id TEXT, product_name TEXT NOT NULL,
                brand TEXT, category TEXT, offer_price REAL NOT NULL,
                original_price REAL, unit TEXT, quantity_deal TEXT,
                valid_from DATE, valid_to DATE, scraped_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY, menu_id TEXT, day TEXT, action TEXT,
                details TEXT, created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS price_history (
                id SERIAL PRIMARY KEY, store_id TEXT, product_name TEXT NOT NULL,
                brand TEXT, category TEXT, offer_price REAL NOT NULL,
                original_price REAL, unit TEXT, quantity_deal TEXT,
                valid_from DATE, valid_to DATE, scraped_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS recipe_stats (
                recipe_id TEXT PRIMARY KEY, times_selected INTEGER DEFAULT 0,
                times_swapped_away INTEGER DEFAULT 0, times_liked INTEGER DEFAULT 0,
                times_disliked INTEGER DEFAULT 0, last_selected TIMESTAMP,
                updated_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS swap_log (
                id SERIAL PRIMARY KEY, old_recipe_id TEXT, old_recipe_title TEXT,
                new_recipe_id TEXT, new_recipe_title TEXT, day TEXT, reason TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS preference_log (
                id SERIAL PRIMARY KEY, household_size INTEGER, num_dinners INTEGER,
                has_children BOOLEAN, dietary_restrictions TEXT, lifestyle_preferences TEXT,
                budget_per_week INTEGER, created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS generation_log (
                id SERIAL PRIMARY KEY, menu_id TEXT, ai_provider TEXT,
                recipe_count INTEGER, total_cost REAL, total_savings REAL,
                offer_count INTEGER, generation_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        await conn.execute("""
            INSERT INTO stores (id, name, city, url, scraper_class)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO NOTHING
        """, "ica-maxi-1004097", "Maxi ICA Stormarknad Orebro Boglundsangen",
             "Orebro", "https://www.ica.se/erbjudanden/maxi-ica-stormarknad-orebro-boglundsangen-1004097/",
             "IcaMaxiScraper")
    logger.info("PostgreSQL initialized")


# --- Unified interface ---

async def _save_price_history(offers: list[Offer]):
    """Append all offers to price_history — never overwritten."""
    if _is_postgres():
        pool = await _pg_get_pool()
        async with pool.acquire() as conn:
            for o in offers:
                await conn.execute("""
                    INSERT INTO price_history (store_id, product_name, brand, category,
                        offer_price, original_price, unit, quantity_deal, valid_from, valid_to)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                """, o.store_id, o.product_name, o.brand, o.category,
                     o.offer_price, o.original_price, o.unit, o.quantity_deal,
                     o.valid_from, o.valid_to)
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            for o in offers:
                await db.execute(
                    """INSERT INTO price_history (store_id, product_name, brand, category,
                        offer_price, original_price, unit, quantity_deal, valid_from, valid_to)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (o.store_id, o.product_name, o.brand, o.category,
                     o.offer_price, o.original_price, o.unit, o.quantity_deal,
                     o.valid_from.isoformat(), o.valid_to.isoformat()))
            await db.commit()
    logger.info(f"Saved {len(offers)} entries to price_history")


async def save_offers(offers: list[Offer]):
    # Also save to permanent history
    await _save_price_history(offers)
    if _is_postgres():
        pool = await _pg_get_pool()
        async with pool.acquire() as conn:
            for o in offers:
                await conn.execute("""
                    INSERT INTO offers (id, store_id, product_name, brand, category, offer_price,
                        original_price, unit, quantity_deal, max_per_household,
                        valid_from, valid_to, requires_membership, image_url, raw_text)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
                    ON CONFLICT (id) DO UPDATE SET offer_price=$6, original_price=$7
                """, o.id, o.store_id, o.product_name, o.brand, o.category,
                     o.offer_price, o.original_price, o.unit, o.quantity_deal,
                     o.max_per_household, o.valid_from, o.valid_to,
                     o.requires_membership, o.image_url, o.raw_text)
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            for o in offers:
                await db.execute(
                    """INSERT OR REPLACE INTO offers
                       (id, store_id, product_name, brand, category, offer_price,
                        original_price, unit, quantity_deal, max_per_household,
                        valid_from, valid_to, requires_membership, image_url, raw_text)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (o.id, o.store_id, o.product_name, o.brand, o.category,
                     o.offer_price, o.original_price, o.unit, o.quantity_deal,
                     o.max_per_household, o.valid_from.isoformat(), o.valid_to.isoformat(),
                     o.requires_membership, o.image_url, o.raw_text))
            await db.commit()


async def save_recipes(recipes: list[Recipe]):
    if _is_postgres():
        pool = await _pg_get_pool()
        async with pool.acquire() as conn:
            for r in recipes:
                await conn.execute("""
                    INSERT INTO recipes (id, title, source_url, source, servings, cook_time_minutes,
                        difficulty, tags, diet_labels, ingredients, instructions,
                        image_url, rating, rating_count, nutrition, cooking_method)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                    ON CONFLICT (id) DO UPDATE SET rating=$13, rating_count=$14
                """, r.id, r.title, r.source_url, r.source, r.servings,
                     r.cook_time_minutes, r.difficulty, json.dumps(r.tags),
                     json.dumps(r.diet_labels),
                     json.dumps([i.model_dump() for i in r.ingredients]),
                     json.dumps(r.instructions), r.image_url, r.rating, r.rating_count,
                     json.dumps(r.nutrition.model_dump() if r.nutrition else None),
                     r.cooking_method)
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            for r in recipes:
                await db.execute(
                    """INSERT OR REPLACE INTO recipes
                       (id, title, source_url, source, servings, cook_time_minutes,
                        difficulty, tags, diet_labels, ingredients, instructions,
                        image_url, rating, rating_count, nutrition, cooking_method)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (r.id, r.title, r.source_url, r.source, r.servings,
                     r.cook_time_minutes, r.difficulty, json.dumps(r.tags),
                     json.dumps(r.diet_labels),
                     json.dumps([i.model_dump() for i in r.ingredients]),
                     json.dumps(r.instructions), r.image_url, r.rating, r.rating_count,
                     json.dumps(r.nutrition.model_dump() if r.nutrition else None),
                     r.cooking_method))
            await db.commit()


def _parse_row(r: dict) -> dict:
    """Parse JSON columns from a recipe row."""
    r["tags"] = json.loads(r["tags"]) if r.get("tags") else []
    r["diet_labels"] = json.loads(r["diet_labels"]) if r.get("diet_labels") else []
    r["ingredients"] = json.loads(r["ingredients"]) if r.get("ingredients") else []
    r["instructions"] = json.loads(r["instructions"]) if r.get("instructions") else []
    return r


async def get_all_recipes() -> list[dict]:
    if _is_postgres():
        pool = await _pg_get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM recipes")
            return [_parse_row(dict(r)) for r in rows]
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute("SELECT * FROM recipes")
            return [_parse_row(dict(row)) async for row in rows]


async def get_current_offers(store_id: str, category: Optional[str] = None) -> list[dict]:
    if _is_postgres():
        pool = await _pg_get_pool()
        async with pool.acquire() as conn:
            if category:
                cats = [c.strip() for c in category.split(",")]
                rows = await conn.fetch(
                    "SELECT * FROM offers WHERE store_id=$1 AND valid_to >= CURRENT_DATE AND category = ANY($2)",
                    store_id, cats)
            else:
                rows = await conn.fetch(
                    "SELECT * FROM offers WHERE store_id=$1 AND valid_to >= CURRENT_DATE", store_id)
            return [dict(r) for r in rows]
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM offers WHERE store_id = ? AND valid_to >= date('now')"
            params: list = [store_id]
            if category:
                cats = [c.strip() for c in category.split(",")]
                placeholders = ",".join("?" * len(cats))
                query += f" AND category IN ({placeholders})"
                params.extend(cats)
            rows = await db.execute(query, params)
            return [dict(row) async for row in rows]
