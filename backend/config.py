from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    ica_store_id: str = "ica-maxi-1004097"
    ica_store_url: str = "https://www.ica.se/erbjudanden/maxi-ica-stormarknad-orebro-boglundsangen-1004097/"
    scrape_interval_hours: int = 24
    database_url: str = "sqlite:///./veckosmak.db"
    app_env: str = "development"
    app_port: int = 8000
    frontend_url: str = "http://localhost:5173"
    max_menu_generations_per_hour: int = 20
    max_swaps_per_menu: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
