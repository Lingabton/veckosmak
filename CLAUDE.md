# VECKOSMAK — MVP Pilot: Claude Code Instruktioner

## Projektöversikt

Bygg en AI-driven menyplaneringstjänst som:
1. Hämtar veckans erbjudanden från ICA Maxi Boglundsängen (Örebro)
2. Matchar erbjudandena mot riktiga recept
3. Genererar personliga veckomenyer optimerade för pris
4. Visar inköpslista med uppskattad besparing

**Målgrupp MVP:** Öppen pilot — börjar med grundaren, sedan testfamiljer i Örebro.
**Interaktion:** Enkel, responsiv webbsida.
**Receptkälla:** Scrapade/kända recept (ica.se/recept som primär källa).
**Butik MVP:** ICA Maxi Boglundsängen (butiks-ID: 1004097). Arkitektur stödjer flera butiker.

---

## Tech Stack

| Komponent | Val | Motivering |
|-----------|-----|------------|
| Backend | **Python (FastAPI)** | Enkelt, snabbt, bra scraping-stöd |
| Frontend | **React (Vite + Tailwind)** | Modern, snabb, lätt att deploya |
| Databas | **SQLite → PostgreSQL** | SQLite för MVP (noll config), enkel migration |
| AI | **Anthropic Claude API** | Receptmatchning, menyoptimering |
| Scraping | **httpx + BeautifulSoup** | Robust, async-stöd |
| Deploy | **Railway / Fly.io / Render** | Enkel deploy, gratis tier |

---

## Mappstruktur (Monorepo)

```
veckosmak/
├── README.md
├── .env.example              # API-nycklar, config
├── .gitignore
│
├── backend/
│   ├── main.py               # FastAPI app, routes
│   ├── config.py             # Settings, environment
│   ├── requirements.txt
│   │
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py           # AbstractScraper klass
│   │   ├── ica_maxi.py       # ICA Maxi-specifik scraper
│   │   └── store_registry.py # Registry: butiks-ID → scraper-klass
│   │
│   ├── recipes/
│   │   ├── __init__.py
│   │   ├── scraper.py        # Hämta recept från ica.se/recept
│   │   ├── models.py         # Recipe datamodell
│   │   └── cache.py          # Lokal receptcache (SQLite)
│   │
│   ├── planner/
│   │   ├── __init__.py
│   │   ├── matcher.py        # Matcha erbjudanden → recept
│   │   ├── optimizer.py      # AI-driven menyoptimering
│   │   └── savings.py        # Beräkna besparing
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── offer.py          # Offer datamodell
│   │   ├── menu.py           # WeeklyMenu datamodell
│   │   ├── shopping_list.py  # ShoppingList datamodell
│   │   └── user_prefs.py     # UserPreferences datamodell
│   │
│   └── db/
│       ├── __init__.py
│       ├── database.py       # SQLite connection, migrations
│       └── schema.sql        # Tabellstruktur
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── PreferencesForm.jsx    # Inställningar: pers, middagar, budget, kost
│   │   │   ├── WeeklyMenu.jsx         # Visa veckomeny med recept
│   │   │   ├── RecipeCard.jsx         # Enskilt recept med ingredienser
│   │   │   ├── ShoppingList.jsx       # Inköpslista med priser
│   │   │   ├── SavingsBanner.jsx      # "Du sparar X kr denna vecka"
│   │   │   ├── SwapRecipe.jsx         # Byt ut ett recept
│   │   │   └── OfferHighlights.jsx    # Veckans bästa erbjudanden
│   │   ├── hooks/
│   │   │   └── useMenu.js             # Fetch + state management
│   │   └── styles/
│   │       └── globals.css
│   │
│   └── public/
│       └── favicon.svg
│
└── scripts/
    ├── scrape_offers.py      # Manuell körning: hämta veckans erbjudanden
    ├── scrape_recipes.py     # Bygg/uppdatera receptdatabas
    └── seed_data.py          # Seed testdata för utveckling
```

---

## Datamodeller

### Offer (Erbjudande)

```python
from pydantic import BaseModel
from datetime import date
from typing import Optional

class Offer(BaseModel):
    id: str                        # Unikt ID (genererat)
    store_id: str                  # "ica-maxi-boglundsangen-1004097"
    product_name: str              # "Färsk kycklingfilé"
    brand: Optional[str]           # "Kronfågel"
    category: str                  # "meat", "fish", "dairy", "produce", "pantry", "bakery", "frozen"
    offer_price: float             # 119.0
    original_price: Optional[float] # 160.0
    unit: str                      # "kr/kg", "kr/st", "kr/förp"
    quantity_deal: Optional[str]   # "2 för 69 kr"
    max_per_household: Optional[int] # 1
    valid_from: date
    valid_to: date
    requires_membership: bool      # Stammis-pris?
    image_url: Optional[str]
    raw_text: str                  # Originaltext från scraping (för debugging)
```

### Recipe (Recept)

```python
class Ingredient(BaseModel):
    name: str                      # "kycklingfilé"
    amount: float                  # 600
    unit: str                      # "g"
    category: str                  # "meat" — matchbar mot Offer.category
    is_pantry_staple: bool         # salt, peppar, olja = True (behövs ej köpas)

class Recipe(BaseModel):
    id: str
    title: str                     # "Kyckling med ugnsrostade grönsaker"
    source_url: Optional[str]      # Länk till ica.se-recept
    source: str                    # "ica.se", "koket.se", "ai-generated"
    servings: int                  # Basportioner
    cook_time_minutes: int
    difficulty: str                # "easy", "medium", "hard"
    tags: list[str]                # ["vardag", "barnvänlig", "snabb", "vegetarisk", ...]
    diet_labels: list[str]         # ["vegetarian", "vegan", "glutenfree", "dairyfree", "lactosefree"]
    ingredients: list[Ingredient]
    instructions: list[str]        # Steg-för-steg
    image_url: Optional[str]
```

### UserPreferences (Användarpreferenser)

```python
class UserPreferences(BaseModel):
    household_size: int            # Antal personer (1-8)
    num_dinners: int               # Antal middagar per vecka (3-7)
    budget_per_week: Optional[int] # Max budget i kr (None = ingen gräns)
    max_cook_time: Optional[int]   # Max tillagningstid i minuter
    dietary_restrictions: list[str] # ["vegetarian", "glutenfree", "dairyfree", "lactosefree"]
    disliked_ingredients: list[str] # ["räkor", "selleri", "koriander"]
    store_id: str                  # Butik att hämta erbjudanden från
```

### WeeklyMenu (Veckomeny)

```python
class PlannedMeal(BaseModel):
    day: str                       # "monday", "tuesday", ...
    recipe: Recipe
    scaled_servings: int           # Anpassat till hushållsstorlek
    offer_matches: list[Offer]     # Vilka erbjudanden som matchar
    estimated_cost: float          # Kostnad med erbjudanden
    estimated_cost_without_offers: float  # Kostnad utan erbjudanden

class WeeklyMenu(BaseModel):
    id: str
    week_number: int
    year: int
    store_id: str
    preferences: UserPreferences
    meals: list[PlannedMeal]
    shopping_list: "ShoppingList"
    total_cost: float
    total_cost_without_offers: float
    total_savings: float
    savings_percentage: float
    generated_at: str              # ISO timestamp
```

### ShoppingList (Inköpslista)

```python
class ShoppingItem(BaseModel):
    ingredient_name: str           # "Kycklingfilé"
    total_amount: float            # Aggregerat från alla recept
    unit: str
    category: str                  # För gruppering i butiken
    matched_offer: Optional[Offer] # Kopplat erbjudande
    estimated_price: float
    is_on_offer: bool

class ShoppingList(BaseModel):
    items: list[ShoppingItem]
    total_estimated_cost: float
    items_on_offer: int
    items_not_on_offer: int
```

---

## API Endpoints

### MVP Endpoints (Bygg dessa först)

```
GET  /api/health                     → { status: "ok", version: "0.1.0" }

GET  /api/offers                     → Lista veckans erbjudanden
     ?store_id=ica-maxi-1004097       (default: ICA Maxi Boglundsängen)
     ?category=meat,fish              (valfritt filter)

POST /api/menu/generate              → Generera veckomeny
     Body: UserPreferences
     Response: WeeklyMenu

POST /api/menu/swap                  → Byt ut ett recept i menyn
     Body: { menu_id, day, reason? }
     Response: PlannedMeal (nytt förslag)

GET  /api/recipes                    → Lista alla recept i cachen
     ?tags=vardag,barnvänlig
     ?diet=vegetarian
     ?max_time=30

GET  /api/stores                     → Lista tillgängliga butiker
```

### Framtida Endpoints (Bygg inte nu)

```
POST /api/user/register
POST /api/user/login
GET  /api/menu/history
POST /api/shopping-list/export       → PDF, delbar länk
POST /api/shopping-list/to-cart      → Skicka till ICA online
```

---

## Scraping-strategi

### ICA erbjudanden — Primär källa

**URL:** `https://www.ica.se/erbjudanden/maxi-ica-stormarknad-orebro-boglundsangen-1004097/`

Sidan laddar erbjudanden dynamiskt. Strategi:

1. **Försök 1: Direkt HTML-scraping**
   - Hämta sidan med httpx
   - Parsa tillgängliga erbjudanden med BeautifulSoup
   - Många erbjudanden finns direkt i initial HTML

2. **Försök 2: ICA API (om möjligt)**
   - Inspektera nätverksanrop i browsern
   - ICA kan ha ett internt JSON API för erbjudanden
   - URL-mönster: `https://handlaprivatkund.ica.se/api/...`

3. **Fallback: Tredjepartskällor**
   - bastaerbjudanden.se har OCR-data från reklamblad
   - e-magin.se hostar PDF-reklambladet

**Scraper-struktur:**

```python
# backend/scrapers/base.py
from abc import ABC, abstractmethod

class AbstractScraper(ABC):
    @abstractmethod
    async def fetch_offers(self, store_id: str) -> list[Offer]:
        """Hämta veckans erbjudanden."""
        pass
    
    @abstractmethod
    def get_store_info(self, store_id: str) -> dict:
        """Returnera butiksinfo (namn, adress, etc)."""
        pass

# backend/scrapers/store_registry.py
STORE_REGISTRY = {
    "ica-maxi-1004097": {
        "name": "Maxi ICA Stormarknad Örebro Boglundsängen",
        "scraper": "IcaMaxiScraper",
        "url": "https://www.ica.se/erbjudanden/maxi-ica-stormarknad-orebro-boglundsangen-1004097/",
        "city": "Örebro",
    }
    # Framtida butiker läggs till här
}
```

### ICA Recept — Receptkälla

**URL:** `https://www.ica.se/recept/`

Strategi:
1. Scrapa receptlistor per kategori (vardagsmat, barnfavoriter, budget, etc.)
2. För varje recept: hämta titel, ingredienser (med mängd och enhet), instruktioner, tid, tags
3. Cacha i SQLite — recepten ändras sällan
4. Bygg initialt en bas på **200–500 recept** som täcker vardagsmat
5. Normalisera ingrediensnamn för matchning (t.ex. "kycklingfilé" matchar "Färsk kycklingfilé Kronfågel")

**Ingrediensnormalisering är kritisk:**

```python
# backend/recipes/normalizer.py

# Mappa receptingredienser → erbjudande-kategorier
INGREDIENT_CATEGORY_MAP = {
    "kycklingfilé": "meat",
    "kycklinglårfilé": "meat",
    "laxfilé": "fish",
    "nötfärs": "meat",
    "falukorv": "meat",
    "hushållsost": "dairy",
    "mjölk": "dairy",
    "potatis": "produce",
    "morötter": "produce",
    "lök": "produce",
    # ... bygg ut iterativt
}

# Fuzzy matching för att koppla receptingredienser till erbjudanden
# Använd Claude API som fallback för svåra matchningar
```

---

## AI-integration (Claude API)

### Användningsområde 1: Menyoptimering

Huvudanvändningen. Skicka erbjudanden + receptkatalog + preferenser till Claude,
få tillbaka en optimerad veckomeny.

```python
# backend/planner/optimizer.py

MENU_SYSTEM_PROMPT = """
Du är en svensk menyplanerare. Din uppgift är att skapa en veckomeny
som maximerar användningen av butikens veckoerrbjudanden.

REGLER:
1. Prioritera recept som använder ingredienser som är på erbjudande
2. Variera proteinkällor över veckan (inte kyckling varje dag)
3. Blanda snabba (<20 min) och långsammare rätter
4. Respektera alltid användarens kostval och allergipreferenser
5. Barnvänliga rätter om hushållet har barn (household_size > 2)
6. Håll dig inom budget om angiven
7. Returnera ALLTID giltig JSON enligt schemat nedan

SVARSFORMAT:
Returnera en JSON-array med objekt:
{
  "meals": [
    {
      "day": "monday",
      "recipe_id": "...",
      "reasoning": "Kort motivering varför just detta recept valdes"
    }
  ]
}
"""

async def generate_menu(
    offers: list[Offer],
    recipes: list[Recipe], 
    preferences: UserPreferences
) -> dict:
    """Generera optimerad veckomeny med Claude."""
    
    # Filtrera recept baserat på kostval
    eligible_recipes = filter_by_diet(recipes, preferences)
    
    # Förbereda kontext
    offers_text = format_offers_for_prompt(offers)
    recipes_text = format_recipes_for_prompt(eligible_recipes)
    prefs_text = format_preferences_for_prompt(preferences)
    
    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=MENU_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""
Veckans erbjudanden:
{offers_text}

Tillgängliga recept:
{recipes_text}

Användarens preferenser:
{prefs_text}

Skapa en veckomeny med {preferences.num_dinners} middagar.
"""
        }]
    )
    
    return parse_menu_response(response)
```

### Användningsområde 2: Ingrediensmatchning (fallback)

```python
# När fuzzy matching inte räcker — fråga Claude
MATCH_PROMPT = """
Matcha dessa receptingredienser mot butikens erbjudanden.
Returnera JSON med matchningar.

Ingredienser: {ingredients}
Erbjudanden: {offers}
"""
```

### Användningsområde 3: Receptbyte

```python
SWAP_PROMPT = """
Användaren vill byta ut {current_recipe} på {day}.
Anledning: {reason}

Föreslå ETT alternativt recept från listan som:
- Fortfarande utnyttjar veckans erbjudanden
- Är annorlunda i smak/stil jämfört med resten av menyn
- Passar användarens preferenser
"""
```

### API-kostnadskontroll

- Använd `claude-sonnet-4-20250514` (inte Opus) — billigare, tillräckligt bra
- Cacha menyer — samma preferenser + samma veckas erbjudanden = samma resultat
- Begränsa antal swaps per session (max 5)
- Logga token-användning per request

---

## Frontend-specifikation

### Sidor / Vyer

**1. Startsida / Preferensformulär**
- Välj hushållsstorlek (slider: 1–8 personer)
- Antal middagar per vecka (slider: 3–7)
- Veckobudget (valfritt, slider: 300–1500 kr, eller "ingen gräns")
- Max tillagningstid (valfritt: 15/20/30/45/60+ min)
- Kostval (checkboxar: vegetarisk, vegan, glutenfri, laktosfri)
- Ingredienser att undvika (tags-input med autocomplete)
- **CTA-knapp:** "Skapa min veckomeny →"

**2. Veckomenyn**
- Visar vardagar (mån–fre eller mån–sön beroende på val)
- Varje dag: receptkort med bild, titel, tid, och vilka erbjudanden som används
- Klickbar → expanderar till fullt recept
- "Byt recept"-knapp på varje dag
- Besparingsbanner högst upp: "Du sparar ca 138 kr (21%) denna vecka"

**3. Inköpslista**
- Grupperad per butikskategori (Frukt & Grönt, Kött & Fisk, Mejeri, etc.)
- Varje vara: namn, mängd, pris, och om den är på erbjudande (markerad)
- Checkbox för att bocka av
- Total kostnad + total besparing
- "Kopiera till urklipp"-knapp
- (Framtida: "Skicka till ICA online")

**4. Veckans erbjudanden (separat vy)**
- Alla matrelevanta erbjudanden i grid
- Filtrera per kategori
- Visa ordinarie pris vs erbjudandepris
- Visa giltighetsperiod

### Design

- **Färgpalett:** Fräscht, skandinavisk matinspiration. Vit bakgrund, accentfärg grön (#2D7D46 — ICA-inspirerad men ej identisk). Varma toner för mat-bilder.
- **Typsnitt:** System font stack (snabb laddning)
- **Responsivt:** Mobile-first. Fungerar lika bra på telefon som desktop.
- **Laddningstillstånd:** Skeleton screens under AI-generering (~3-5 sek)
- **Språk:** Svenska, genomgående

---

## Databasschema (SQLite MVP)

```sql
-- Butiker
CREATE TABLE stores (
    id TEXT PRIMARY KEY,           -- "ica-maxi-1004097"
    name TEXT NOT NULL,
    city TEXT,
    url TEXT,
    scraper_class TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Erbjudanden
CREATE TABLE offers (
    id TEXT PRIMARY KEY,
    store_id TEXT REFERENCES stores(id),
    product_name TEXT NOT NULL,
    brand TEXT,
    category TEXT NOT NULL,
    offer_price REAL NOT NULL,
    original_price REAL,
    unit TEXT,
    quantity_deal TEXT,
    max_per_household INTEGER,
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,
    requires_membership BOOLEAN DEFAULT FALSE,
    image_url TEXT,
    raw_text TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_offers_store_week ON offers(store_id, valid_from, valid_to);
CREATE INDEX idx_offers_category ON offers(category);

-- Recept
CREATE TABLE recipes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_url TEXT,
    source TEXT NOT NULL,           -- "ica.se", "koket.se"
    servings INTEGER,
    cook_time_minutes INTEGER,
    difficulty TEXT,
    tags TEXT,                      -- JSON array
    diet_labels TEXT,               -- JSON array
    ingredients TEXT NOT NULL,      -- JSON array of Ingredient objects
    instructions TEXT NOT NULL,     -- JSON array of strings
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_recipes_tags ON recipes(tags);

-- Genererade menyer (för caching och historik)
CREATE TABLE generated_menus (
    id TEXT PRIMARY KEY,
    store_id TEXT REFERENCES stores(id),
    week_number INTEGER,
    year INTEGER,
    preferences TEXT NOT NULL,      -- JSON: UserPreferences
    menu_data TEXT NOT NULL,        -- JSON: WeeklyMenu
    total_cost REAL,
    total_savings REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_menus_week ON generated_menus(store_id, year, week_number);

-- Feedback (för att lära sig vad som funkar)
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_id TEXT REFERENCES generated_menus(id),
    day TEXT,
    action TEXT,                    -- "swapped", "liked", "disliked"
    details TEXT,                   -- JSON med anledning/nytt recept
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Bygginstruktioner — Steg för steg

### Fas 1: Grund (Dag 1-2)

**Steg 1: Projektsetup**
```bash
mkdir veckosmak && cd veckosmak
git init

# Backend
mkdir -p backend/{scrapers,recipes,planner,models,db}
touch backend/main.py backend/config.py backend/requirements.txt

# Frontend
npm create vite@latest frontend -- --template react
cd frontend && npm install && npm install -D tailwindcss @tailwindcss/vite

# Environment
cp .env.example .env
# Fyll i: ANTHROPIC_API_KEY
```

**Steg 2: Datamodeller + databas**
- Skapa alla Pydantic-modeller (se ovan)
- Skapa SQLite-schema
- Skapa database.py med connection management
- Kör seed_data.py med testdata

**Steg 3: ICA erbjudande-scraper**
- Implementera IcaMaxiScraper
- Testa mot live-sidan
- Spara till databasen
- Logga eventuella parse-fel

### Fas 2: Receptmotor (Dag 2-3)

**Steg 4: Receptscraper (ica.se)**
- Scrapa receptkategorier: vardagsmat, snabbt & enkelt, barnfavoriter, budget
- Parsa ingredienser med mängd och enhet
- Normalisera ingrediensnamn
- Spara 200+ recept i databasen

**Steg 5: Ingrediensmatchning**
- Bygg fuzzy matching: receptingrediens → erbjudande
- Testa med verkliga erbjudanden
- Claude API som fallback för svåra matchningar

### Fas 3: AI-menyplanerare (Dag 3-4)

**Steg 6: Claude-integration**
- Implementera optimizer.py
- Testa med riktiga erbjudanden + recept
- Iterera på prompten tills resultaten är bra
- Implementera swap-funktion

**Steg 7: Besparingsberäkning**
- Beräkna kostnad per portion med erbjudandepris
- Beräkna kostnad utan erbjudanden (ordinarie pris)
- Aggregera till veckobesparing
- Hantera "2 för X"-erbjudanden korrekt

### Fas 4: Frontend (Dag 4-6)

**Steg 8: Preferensformulär**
- Responsivt formulär med alla inställningar
- Sparas i localStorage (ingen inloggning i MVP)

**Steg 9: Menyvisning**
- Hämta genererad meny från API
- Visa receptkort med bilder
- Expanderbart recept med ingredienser + instruktioner
- Swap-funktion

**Steg 10: Inköpslista + besparing**
- Aggregerad lista från alla recept
- Grupperad per kategori
- Markera kampanjvaror
- Besparingssummering

### Fas 5: Polish + Deploy (Dag 6-7)

**Steg 11: Error handling + edge cases**
- Vad händer om scraping misslyckas?
- Vad händer om inga erbjudanden matchar?
- Vad händer om Claude API timeout?
- Fallback-menyer?

**Steg 12: Deploy**
- Backend: Railway / Render (gratis tier)
- Frontend: Vercel / Netlify (gratis)
- Schemalägg scraping: cron varje måndag 06:00
- Lägg till basic analytics (Plausible / Umami)

---

## Viktiga designbeslut

### 1. Scraping-resiliens
Scrapern KOMMER att gå sönder förr eller senare. Bygg för det:
- Spara alltid raw_text så du kan debugga
- Ha en fallback: manuell inmatning via admin-endpoint
- Logga alla scraping-körningar med antal hämtade erbjudanden
- Alerting om 0 erbjudanden hämtas en vecka

### 2. Receptkvalitet > kvantitet
200 bra, väl-parsade recept slår 2000 halvdåliga.
Fokusera på:
- Vardagsmiddagar (inte festmat)
- Ingredienser som faktiskt hamnar på erbjudande (kyckling, nötfärs, lax, falukorv, potatis)
- Korrekta mängder och enheter
- Barnvänligt som default

### 3. Besparing måste kännas ärlig
- Jämför alltid mot ordinariepris från samma butik
- Visa "Uppskattat pris" — aldrig "Exakt pris"
- Inkludera disclaimer: "Priserna är uppskattade baserat på veckans erbjudanden"
- Avrunda inte uppåt (hellre konservativ)

### 4. Mobile first
Majoriteten av användarna kommer öppna detta i telefonen — i butiken eller vid matbordet.
- Stora touch targets
- Inget horisontellt scroll
- Inköpslistan ska vara checkbar med tummen

---

## Framtida utveckling (BYGG INTE NU — men strukturera koden så det går att lägga till)

### Fas 2: Fler butiker
- Lägg till Willys, Coop, Lidl som scrapers via store_registry
- Användaren väljer sin butik
- Jämför erbjudanden mellan butiker ("Du sparar 45 kr mer på Willys denna vecka")

### Fas 3: Användarkonton
- Inloggning (email magic link — inga lösenord)
- Spara preferenser server-side
- Menyhistorik
- "Min receptbok" — favoritrecept

### Fas 4: Smart inlärning
- Spåra vilka recept som byts ut (= dåliga förslag)
- Spåra vilka som behålls (= bra förslag)
- Säsongsanpassning (grillmat sommar, grytor vinter)
- Lär sig familjens smak över tid

### Fas 5: Digital varukorg
- Integration med ICA online (handla.ica.se)
- Generera delbar inköpslista (URL eller QR-kod)
- Push-notification: "Veckans meny är klar!"

### Fas 6: Affärsmodell
- Freemium: 3 gratis recept/vecka, premium = full meny + inköpslista
- Visa besparing: "Du har sparat X kr denna månad" → "Premium kostar 79 kr/mån"
- Eventuellt: affiliate med matbutiker (provision per order)

### Fas 7: Community
- Dela menyer med andra familjer
- Betygsätt recept
- "Veckans populäraste meny i Örebro"

---

## Konfigurationsfil (.env)

```
# API
ANTHROPIC_API_KEY=sk-ant-...

# Scraping
ICA_STORE_ID=ica-maxi-1004097
ICA_STORE_URL=https://www.ica.se/erbjudanden/maxi-ica-stormarknad-orebro-boglundsangen-1004097/
SCRAPE_INTERVAL_HOURS=24

# Database
DATABASE_URL=sqlite:///./veckosmak.db

# App
APP_ENV=development
APP_PORT=8000
FRONTEND_URL=http://localhost:5173

# Rate limiting
MAX_MENU_GENERATIONS_PER_HOUR=20
MAX_SWAPS_PER_MENU=5
```

---

## Testplan

### Manuell testning (MVP)
1. Kör scraper → verifiera att erbjudandena ser korrekta ut
2. Generera meny med default-preferenser → kontrollera att recepten finns och erbjudanden matchar
3. Generera meny med vegetarisk kostval → verifiera att inget kött
4. Byt recept → kontrollera att nytt förslag är annorlunda
5. Kontrollera inköpslista → stämmer mängderna?
6. Kontrollera besparing → rimlig siffra? Ärlig?
7. Testa på mobil → fungerar allt?
8. Testa med 0 erbjudanden → graceful fallback?

### Automatiserade tester (bygg på sikt)
- Unit tests för ingrediensmatchning
- Unit tests för besparingsberäkning
- Integration test: scraper → databas → meny
- Snapshot tests för frontend

---

## Namnförslag

Arbetsnamn: **Veckosmak**

Alternativ att testa med användare:
- Veckosmak ("Veckans smak")
- Matklipp ("Mat + klipp/erbjudande")
- Veckokassen ("Digitala matkassen")
- Middagshjälpen
- Smartlistan

Domän: Kolla tillgänglighet innan du bestämmer.

---

## Sammanfattning: Vad är "klart" i MVP?

En MVP är klar när en testfamilj kan:

1. ✅ Öppna en webbsida
2. ✅ Välja hushållsstorlek, antal middagar, budget och kostval
3. ✅ Få en veckomeny med 3–7 middagar baserade på ICA Maxis erbjudanden
4. ✅ Se varje recept med ingredienser och instruktioner
5. ✅ Byta ut recept de inte vill ha
6. ✅ Se en inköpslista grupperad per kategori
7. ✅ Se hur mycket de sparar jämfört med ordinarie pris

Allt utöver detta är Fas 2+.

---

## Produktriktning (2026-03-31)

### Position
**Från erbjudande till riktig middag**

### Grundprincip
Allt ska bedömas utifrån: *Hjälper detta användaren att förstå hur erbjudanden blir till riktiga middagar, tydlig veckokostnad och färdig inköpslista?* Om nej: inte prioritet.

### Produkten ska signalera
- Erbjudanden som motor
- Middagar som output
- Veckokostnad som beslutsstöd
- Inköpslista som handling
- Besparing som trovärdig effekt

### Produkten ska INTE glida mot
- Allmän receptsajt
- Fluffig AI-meal-planner
- Inspirationsapp utan tydlig ekonomi

### Ekonomi-copy — regler
- ALDRIG "Du sparar -73 kr" (minus framför sparande)
- Besparing ska ALLTID ha förklaring: "jämfört med ordinarie pris"
- Konsekvent terminologi överallt: "Uppskattad veckokostnad", "Beräknad besparing", "Pris per portion"
- Ungefärliga belopp: "Cirka 377 kr"
- Procent: "16 % billigare"

### Ingrediensprislogik — tre typer
1. **Kampanjvara** — grön markering + "på kampanj"
2. **Uppskattad kostnad** — "~3 kr"
3. **Neutral ingrediens** — ingen markering

### "Varför detta recept" — ska vara konkret
Inte "Automatiskt vald baserat på erbjudanden". Utan:
- "3 huvudingredienser på kampanj"
- "Låg kostnad per portion denna vecka"
- "Använder erbjudanden från din butik"

### CTA i hero
- En tydlig primär CTA: "Skapa min veckomeny"
- Under knappen: "Tar cirka 30 sekunder · Gratis · Ingen inloggning"

### Byt-funktionen
Alternativ ska visa: pris/portion, tid, betyg, antal erbjudanden, om billigare/dyrare
Ska kännas smart, inte slumpmässigt.

### Inköpslistan
Optimerad för butik: stor checkzon, tydlig radseparering, lite visuellt brus.
Ska kunna användas med en hand i butik.

### P1 (fixa nu)
1. Förklara besparingen tydligt
2. Rätta all ekonomi-copy
3. Tydligare CTA i hero
4. Stärk "Varför detta recept"
5. Tydliggör prislogik i ingredienslistan
6. Gör erbjudandesidan mer nyttig
7. Förbättra byt-funktionen
8. Förenkla inköpslistan för butik

### P2 (efter P1)
9. Förbättra mobil-header
10. Mer proof på startsidan
11. Skärp spara-copy
12. Butiksväljaren starkare

### P3 (planera, bygg inte ännu)
13. Sparad profil
14. Historik/tidigare veckor
15. Ta bort halvfärdiga element
