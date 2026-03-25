"""Build/update the recipe database by scraping ica.se."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.database import init_db, save_recipes
from backend.recipes.scraper import scrape_all_recipes

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def main():
    max_recipes = int(sys.argv[1]) if len(sys.argv) > 1 else 600

    await init_db()

    print(f"Scrapar recept fran ica.se (max {max_recipes})...")
    recipes = await scrape_all_recipes(max_recipes=max_recipes)

    if not recipes:
        print("Inga recept hittades!")
        return

    print(f"\nHittade {len(recipes)} recept. Exempel:")
    for r in recipes[:5]:
        ing_count = len(r.ingredients)
        labels = ", ".join(r.diet_labels) if r.diet_labels else "-"
        print(f"  {r.title} ({r.cook_time_minutes} min, {ing_count} ingredienser, {labels})")

    await save_recipes(recipes)
    print(f"\nSparat {len(recipes)} recept till databasen.")


if __name__ == "__main__":
    asyncio.run(main())
