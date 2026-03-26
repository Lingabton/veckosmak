"""Scrape recipes from ica.se using JSON-LD structured data."""

import asyncio
import json
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from backend.models.recipe import Ingredient, Nutrition, Recipe

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "sv-SE,sv;q=0.9",
}

# Expanded categories for more recipe coverage
RECIPE_CATEGORIES = [
    # Core everyday
    "/recept/middag/",
    "/recept/vardagsmat/",
    "/recept/husmanskost/",
    "/recept/snabbt-och-enkelt/",
    "/recept/billig-mat/",
    "/recept/barnens-favoriter/",
    "/recept/restmat/",
    # Proteins
    "/recept/kyckling/",
    "/recept/kycklingfile/",
    "/recept/kottfars/",
    "/recept/notfars/",
    "/recept/fisk/",
    "/recept/lax/",
    "/recept/torsk/",
    "/recept/falukorv/",
    "/recept/korv/",
    "/recept/flask/",
    "/recept/biff/",
    "/recept/lamm/",
    "/recept/raker/",
    "/recept/kassler/",
    "/recept/kottbullar/",
    # Cooking method / type
    "/recept/pasta/",
    "/recept/soppa/",
    "/recept/gratang/",
    "/recept/gryta/",
    "/recept/wok/",
    "/recept/sallad/",
    "/recept/potatis/",
    "/recept/ris/",
    "/recept/pizza/",
    "/recept/tacos/",
    "/recept/wrap/",
    "/recept/hamburgare/",
    "/recept/pannkakor/",
    "/recept/omelett/",
    "/recept/plattjarn/",
    # Diet / lifestyle
    "/recept/vegetarisk/",
    "/recept/vegansk/",
    "/recept/glutenfritt/",
    "/recept/laktosfritt/",
    "/recept/lchf/",
    "/recept/nyttig-mat/",
    "/recept/proteinrik-mat/",
    # Seasonal
    "/recept/grillrecept/",
    "/recept/sommarmat/",
    "/recept/host/",
    "/recept/vinter/",
    "/recept/julmat/",
]

PAGES_PER_CATEGORY = 3

PANTRY_STAPLES = {
    "salt", "peppar", "svartpeppar", "olja", "olivolja", "rapsolja", "smör",
    "socker", "strösocker", "vatten", "kallt vatten", "ljummet vatten",
    "kokande vatten", "vitpeppar", "malen peppar",
}

# Order matters! More specific matches MUST come before generic ones.
# "kycklingfond" must match "fond" (pantry) before "kyckling" (meat).
INGREDIENT_CATEGORY_MAP_ORDERED = [
    # Pantry — check FIRST (before proteins catch "kycklingfond" etc)
    ("kycklingfond", "pantry"), ("kyckling fond", "pantry"),
    ("kalvfond", "pantry"), ("grönsaksfond", "pantry"),
    ("fond", "pantry"), ("buljong", "pantry"),
    ("tomatpuré", "pantry"), ("krossade tomater", "pantry"),
    ("passerade tomater", "pantry"), ("kokosmjölk", "pantry"),
    ("soja", "pantry"), ("dijonsenap", "pantry"), ("senap", "pantry"),
    ("vinäger", "pantry"), ("honung", "pantry"), ("ströbröd", "pantry"),
    ("pasta", "pantry"), ("spaghetti", "pantry"), ("penne", "pantry"),
    ("ris", "pantry"), ("bulgur", "pantry"), ("couscous", "pantry"),
    ("mjöl", "pantry"), ("vetemjöl", "pantry"),
    # Herbs & produce
    ("basilika", "produce"), ("koriander", "produce"), ("persilja", "produce"),
    ("dill", "produce"), ("rosmarin", "produce"), ("timjan", "produce"),
    ("mynta", "produce"), ("oregano", "produce"), ("gräslök", "produce"),
    ("rucola", "produce"),
    ("potatis", "produce"), ("morot", "produce"), ("morötter", "produce"),
    ("lök", "produce"), ("gul lök", "produce"), ("rödlök", "produce"),
    ("vitlök", "produce"), ("tomat", "produce"), ("tomater", "produce"),
    ("paprika", "produce"), ("gurka", "produce"), ("broccoli", "produce"),
    ("blomkål", "produce"), ("spenat", "produce"), ("sallad", "produce"),
    ("purjolök", "produce"), ("squash", "produce"), ("zucchini", "produce"),
    ("avokado", "produce"), ("champinjoner", "produce"), ("svamp", "produce"),
    ("selleri", "produce"), ("citron", "produce"), ("lime", "produce"),
    ("ingefära", "produce"), ("chili", "produce"),
    # Meat
    ("kyckling", "meat"), ("kycklingfilé", "meat"), ("kycklinglår", "meat"),
    ("kycklingklubba", "meat"), ("nötfärs", "meat"), ("blandfärs", "meat"),
    ("fläskfärs", "meat"), ("färs", "meat"), ("fläskfilé", "meat"),
    ("fläskkarré", "meat"), ("fläskkotlett", "meat"), ("bacon", "meat"),
    ("skinka", "meat"), ("falukorv", "meat"), ("korv", "meat"), ("kassler", "meat"),
    ("köttbullar", "meat"), ("entrecôte", "meat"), ("biff", "meat"),
    ("kalkon", "meat"), ("lamm", "meat"), ("chorizo", "meat"),
    ("pancetta", "meat"), ("prosciutto", "meat"),
    # Fish
    ("lax", "fish"), ("laxfilé", "fish"), ("torsk", "fish"), ("torskfilé", "fish"),
    ("räkor", "fish"), ("sej", "fish"), ("tonfisk", "fish"), ("fisk", "fish"),
    ("sill", "fish"), ("makrill", "fish"), ("pangasius", "fish"),
    # Dairy
    ("mjölk", "dairy"), ("grädde", "dairy"), ("vispgrädde", "dairy"),
    ("matlagningsgrädde", "dairy"), ("crème fraiche", "dairy"),
    ("gräddfil", "dairy"), ("yoghurt", "dairy"), ("kvarg", "dairy"),
    ("ost", "dairy"), ("riven ost", "dairy"), ("mozzarella", "dairy"),
    ("parmesan", "dairy"), ("smör", "dairy"), ("ägg", "dairy"),
]


def classify_ingredient(name: str) -> str:
    """Classify ingredient by category. Uses ordered list — most specific first."""
    name_lower = name.lower().strip()
    for key, cat in INGREDIENT_CATEGORY_MAP_ORDERED:
        if key in name_lower:
            return cat
    return "other"


def is_pantry_staple(name: str) -> bool:
    return name.lower().strip() in PANTRY_STAPLES


def parse_ingredient_text(text: str) -> Ingredient:
    """Parse ingredient string like '550 g falukorv' into structured data."""
    text = text.strip()
    match = re.match(
        r'^([\d/½¼¾]+(?:\s*[\d/½¼¾]+)?)\s*'
        r'(g|kg|dl|l|ml|cl|msk|tsk|st|krm|port|nypa|knippe)\s+'
        r'(.+)$',
        text, re.IGNORECASE
    )
    if match:
        amount_str = match.group(1).strip()
        unit = match.group(2).strip().lower()
        name = match.group(3).strip()
        amount = parse_amount(amount_str)
    else:
        amount = 0.0
        unit = ""
        name = text
    return Ingredient(
        name=name, amount=amount, unit=unit,
        category=classify_ingredient(name),
        is_pantry_staple=is_pantry_staple(name),
    )


def parse_amount(s: str) -> float:
    s = s.replace("½", "0.5").replace("¼", "0.25").replace("¾", "0.75")
    parts = s.strip().split()
    total = 0.0
    for part in parts:
        if "/" in part:
            num, den = part.split("/", 1)
            try:
                total += float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                pass
        else:
            try:
                total += float(part)
            except ValueError:
                pass
    return total


def parse_cook_time(iso_duration: str) -> int:
    if not iso_duration:
        return 0
    hours = 0
    minutes = 0
    h_match = re.search(r'(\d+)H', iso_duration)
    m_match = re.search(r'(\d+)M', iso_duration)
    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        minutes = int(m_match.group(1))
    return hours * 60 + minutes


def extract_tags(json_ld: dict) -> list[str]:
    tags = []
    categories = json_ld.get("recipeCategory", "")
    if isinstance(categories, str):
        categories = [c.strip() for c in categories.split(",")]
    for cat in categories:
        cat_lower = cat.lower()
        if "middag" in cat_lower or "huvudrätt" in cat_lower:
            tags.append("middag")
        if "lunch" in cat_lower:
            tags.append("lunch")
        if "vegetari" in cat_lower:
            tags.append("vegetarisk")
        if "vegan" in cat_lower:
            tags.append("vegansk")
        if "barn" in cat_lower:
            tags.append("barnvänlig")
        if "grill" in cat_lower:
            tags.append("grill")
        if "snabb" in cat_lower or "enkel" in cat_lower:
            tags.append("snabb")
        if "budget" in cat_lower or "billig" in cat_lower:
            tags.append("budget")
        if "nyttig" in cat_lower or "hälso" in cat_lower:
            tags.append("nyttig")

    # Also check keywords from recipe title
    keywords = json_ld.get("keywords", "")
    if isinstance(keywords, str):
        kw_lower = keywords.lower()
        if "barnvänlig" in kw_lower or "barn" in kw_lower:
            tags.append("barnvänlig")
        if "klassiker" in kw_lower:
            tags.append("klassiker")
        if "husmanskost" in kw_lower:
            tags.append("husmanskost")

    cook_time = parse_cook_time(json_ld.get("totalTime", ""))
    if cook_time and cook_time <= 30:
        tags.append("snabb")

    return list(set(tags))


def extract_diet_labels(ingredients: list[Ingredient]) -> list[str]:
    has_meat = any(i.category == "meat" for i in ingredients)
    has_fish = any(i.category == "fish" for i in ingredients)
    has_dairy = any(i.category == "dairy" for i in ingredients)
    labels = []
    if not has_meat and not has_fish:
        labels.append("vegetarian")
    if not has_meat and not has_fish and not has_dairy:
        labels.append("vegan")
    return labels


def extract_nutrition(json_ld: dict) -> Optional[Nutrition]:
    """Extract nutrition info from JSON-LD."""
    nutr = json_ld.get("nutrition")
    if not nutr or not isinstance(nutr, dict):
        return None
    try:
        def parse_num(val):
            if val is None:
                return None
            s = str(val).replace(",", ".").strip()
            m = re.search(r'[\d.]+', s)
            return float(m.group()) if m else None

        calories = parse_num(nutr.get("calories"))
        protein = parse_num(nutr.get("proteinContent"))
        carbs = parse_num(nutr.get("carbohydrateContent"))
        fat = parse_num(nutr.get("fatContent"))
        if calories or protein:
            return Nutrition(
                calories=int(calories) if calories else None,
                protein=round(protein, 1) if protein else None,
                carbohydrates=round(carbs, 1) if carbs else None,
                fat=round(fat, 1) if fat else None,
            )
    except (ValueError, TypeError):
        pass
    return None


def extract_cooking_method(json_ld: dict, instructions: list[str]) -> Optional[str]:
    """Infer cooking method from instructions and metadata."""
    text = " ".join(instructions).lower()
    method = json_ld.get("cookingMethod", "").lower()
    combined = f"{method} {text}"
    if "ugn" in combined or "grader" in combined or "225°" in combined or "200°" in combined:
        return "ugn"
    if "grill" in combined:
        return "grill"
    if "slow cooker" in combined or "crock" in combined:
        return "slowcooker"
    return "spis"


def extract_rating(json_ld: dict) -> tuple[Optional[float], Optional[int]]:
    """Extract crowd rating from JSON-LD aggregateRating."""
    agg = json_ld.get("aggregateRating")
    if not agg or not isinstance(agg, dict):
        return None, None

    try:
        rating = float(agg.get("ratingValue", 0))
        count = int(agg.get("ratingCount", agg.get("reviewCount", 0)))
        if rating > 0:
            return round(rating, 1), count
    except (ValueError, TypeError):
        pass

    return None, None


def parse_recipe_from_jsonld(json_ld: dict, source_url: str) -> Optional[Recipe]:
    """Parse a Recipe from JSON-LD structured data."""
    try:
        name = json_ld.get("name", "")
        if not name:
            return None

        id_match = re.search(r'-(\d+)/?$', source_url)
        recipe_id = f"ica-{id_match.group(1)}" if id_match else f"ica-{hash(source_url)}"

        raw_ingredients = json_ld.get("recipeIngredient", [])
        ingredients = [parse_ingredient_text(ing) for ing in raw_ingredients]

        raw_instructions = json_ld.get("recipeInstructions", [])
        instructions = []
        for step in raw_instructions:
            if isinstance(step, dict):
                instructions.append(step.get("text", ""))
            elif isinstance(step, str):
                instructions.append(step)

        cook_time = parse_cook_time(json_ld.get("totalTime", ""))
        servings_str = json_ld.get("recipeYield", "4")
        servings = int(re.search(r'\d+', str(servings_str)).group()) if re.search(r'\d+', str(servings_str)) else 4

        tags = extract_tags(json_ld)
        diet_labels = extract_diet_labels(ingredients)
        image_url = json_ld.get("image", "")
        difficulty = "easy" if cook_time <= 30 else "medium" if cook_time <= 60 else "hard"

        rating, rating_count = extract_rating(json_ld)
        nutrition = extract_nutrition(json_ld)
        cooking_method = extract_cooking_method(json_ld, instructions)

        return Recipe(
            id=recipe_id,
            title=name,
            source_url=source_url,
            source="ica.se",
            servings=servings,
            cook_time_minutes=cook_time or 30,
            difficulty=difficulty,
            tags=tags,
            diet_labels=diet_labels,
            ingredients=ingredients,
            instructions=instructions,
            image_url=image_url,
            rating=rating,
            rating_count=rating_count,
            nutrition=nutrition,
            cooking_method=cooking_method,
        )
    except Exception as e:
        logger.error(f"Failed to parse recipe from {source_url}: {e}")
        return None


async def scrape_recipe(client: httpx.AsyncClient, url: str) -> Optional[Recipe]:
    """Scrape a single recipe page."""
    try:
        resp = await client.get(url, headers=HEADERS)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "Recipe":
                        return parse_recipe_from_jsonld(item, url)
            elif isinstance(data, dict) and data.get("@type") == "Recipe":
                return parse_recipe_from_jsonld(data, url)
        except json.JSONDecodeError:
            continue

    logger.warning(f"No JSON-LD recipe data found at {url}")
    return None


async def collect_recipe_urls(client: httpx.AsyncClient) -> set[str]:
    """Collect recipe URLs from category pages."""
    all_urls = set()

    for category in RECIPE_CATEGORIES:
        for page in range(1, PAGES_PER_CATEGORY + 1):
            url = f"https://www.ica.se{category}"
            if page > 1:
                url += f"?page={page}"

            try:
                resp = await client.get(url, headers=HEADERS)
                urls = re.findall(r'/recept/[a-z0-9äåöé-]+-\d+/', resp.text)
                new_urls = {f"https://www.ica.se{u}" for u in urls}
                all_urls.update(new_urls)
                logger.debug(f"{category} page {page}: {len(new_urls)} recipes")
            except httpx.HTTPError as e:
                logger.warning(f"Failed to fetch {url}: {e}")

    logger.info(f"Collected {len(all_urls)} unique recipe URLs")
    return all_urls


async def scrape_all_recipes(max_recipes: int = 600) -> list[Recipe]:
    """Scrape recipes from ica.se. Returns parsed recipes."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        urls = await collect_recipe_urls(client)
        urls = list(urls)[:max_recipes]

        logger.info(f"Scraping {len(urls)} recipes...")
        recipes = []
        for i, url in enumerate(urls):
            recipe = await scrape_recipe(client, url)
            if recipe:
                recipes.append(recipe)

            if (i + 1) % 20 == 0:
                logger.info(f"Progress: {i + 1}/{len(urls)} ({len(recipes)} parsed)")
                await asyncio.sleep(0.5)

        logger.info(f"Scraped {len(recipes)} recipes successfully")
        rated = sum(1 for r in recipes if r.rating)
        logger.info(f"  {rated} recipes have crowd ratings")
        return recipes
