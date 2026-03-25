-- Butiker
CREATE TABLE IF NOT EXISTS stores (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT,
    url TEXT,
    scraper_class TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Erbjudanden
CREATE TABLE IF NOT EXISTS offers (
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

CREATE INDEX IF NOT EXISTS idx_offers_store_week ON offers(store_id, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_offers_category ON offers(category);

-- Recept
CREATE TABLE IF NOT EXISTS recipes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_url TEXT,
    source TEXT NOT NULL,
    servings INTEGER,
    cook_time_minutes INTEGER,
    difficulty TEXT,
    tags TEXT,
    diet_labels TEXT,
    ingredients TEXT NOT NULL,
    instructions TEXT NOT NULL,
    image_url TEXT,
    rating REAL,
    rating_count INTEGER,
    nutrition TEXT,
    cooking_method TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_recipes_tags ON recipes(tags);

-- Genererade menyer
CREATE TABLE IF NOT EXISTS generated_menus (
    id TEXT PRIMARY KEY,
    store_id TEXT REFERENCES stores(id),
    week_number INTEGER,
    year INTEGER,
    preferences TEXT NOT NULL,
    menu_data TEXT NOT NULL,
    total_cost REAL,
    total_savings REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_menus_week ON generated_menus(store_id, year, week_number);

-- Feedback
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_id TEXT REFERENCES generated_menus(id),
    day TEXT,
    action TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
