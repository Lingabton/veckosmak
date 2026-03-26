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

-- Users
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    preferences TEXT,            -- JSON: saved UserPreferences
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Magic link tokens
CREATE TABLE IF NOT EXISTS auth_tokens (
    token TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_auth_email ON auth_tokens(email);

-- Saved menus per user
CREATE TABLE IF NOT EXISTS user_menus (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    week_number INTEGER,
    year INTEGER,
    menu_data TEXT NOT NULL,      -- JSON: full WeeklyMenu
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_menus ON user_menus(user_id, year, week_number);

-- Prishistorik — alla erbjudanden sparas, aldrig överskrivna
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT,
    product_name TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    offer_price REAL NOT NULL,
    original_price REAL,
    unit TEXT,
    quantity_deal TEXT,
    valid_from DATE,
    valid_to DATE,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history(product_name, store_id);
CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(scraped_at);
CREATE INDEX IF NOT EXISTS idx_price_history_category ON price_history(category, scraped_at);

-- Feedback (like/dislike per recept)
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_id TEXT REFERENCES generated_menus(id),
    day TEXT,
    action TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Receptpopularitet — hur ofta varje recept väljs/byts/gillas
CREATE TABLE IF NOT EXISTS recipe_stats (
    recipe_id TEXT PRIMARY KEY,
    times_selected INTEGER DEFAULT 0,
    times_swapped_away INTEGER DEFAULT 0,
    times_liked INTEGER DEFAULT 0,
    times_disliked INTEGER DEFAULT 0,
    last_selected TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Swap-logg — vad byts ut, varför, till vad
CREATE TABLE IF NOT EXISTS swap_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    old_recipe_id TEXT,
    old_recipe_title TEXT,
    new_recipe_id TEXT,
    new_recipe_title TEXT,
    day TEXT,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_swap_log_date ON swap_log(created_at);

-- Preferens-statistik — anonymiserad aggregering
CREATE TABLE IF NOT EXISTS preference_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_size INTEGER,
    num_dinners INTEGER,
    has_children BOOLEAN,
    dietary_restrictions TEXT,    -- JSON array
    lifestyle_preferences TEXT,  -- JSON array
    budget_per_week INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pref_log_date ON preference_log(created_at);

-- Meny-genererings-logg — metadata per generering
CREATE TABLE IF NOT EXISTS generation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_id TEXT,
    ai_provider TEXT,            -- "cloudflare", "claude-sonnet", "claude-haiku", "fallback"
    recipe_count INTEGER,
    total_cost REAL,
    total_savings REAL,
    offer_count INTEGER,
    generation_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gen_log_date ON generation_log(created_at);
