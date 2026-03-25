"""Seed testdata for development."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta
from backend.db.database import init_db, save_offers
from backend.models.offer import Offer


def make_test_offers() -> list[Offer]:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    return [
        Offer(
            id="offer-001",
            store_id="ica-maxi-1004097",
            product_name="Kycklingfile",
            brand="Kronfagel",
            category="meat",
            offer_price=89.0,
            original_price=129.0,
            unit="kr/kg",
            valid_from=week_start,
            valid_to=week_end,
            raw_text="Kycklingfile Kronfagel 89 kr/kg ord.pris 129 kr/kg",
        ),
        Offer(
            id="offer-002",
            store_id="ica-maxi-1004097",
            product_name="Notfars 12%",
            brand="ICA",
            category="meat",
            offer_price=69.0,
            original_price=99.0,
            unit="kr/kg",
            valid_from=week_start,
            valid_to=week_end,
            raw_text="Notfars 12% ICA 69 kr/kg ord.pris 99 kr/kg",
        ),
        Offer(
            id="offer-003",
            store_id="ica-maxi-1004097",
            product_name="Laxfile",
            brand="ICA",
            category="fish",
            offer_price=119.0,
            original_price=169.0,
            unit="kr/kg",
            valid_from=week_start,
            valid_to=week_end,
            raw_text="Laxfile ICA 119 kr/kg ord.pris 169 kr/kg",
        ),
        Offer(
            id="offer-004",
            store_id="ica-maxi-1004097",
            product_name="Falukorv",
            brand="Scan",
            category="meat",
            offer_price=25.0,
            original_price=39.0,
            unit="kr/st",
            valid_from=week_start,
            valid_to=week_end,
            raw_text="Falukorv Scan 25 kr/st ord.pris 39 kr/st",
        ),
        Offer(
            id="offer-005",
            store_id="ica-maxi-1004097",
            product_name="Pasta penne",
            brand="Barilla",
            category="pantry",
            offer_price=15.0,
            original_price=25.0,
            unit="kr/st",
            quantity_deal="2 for 30 kr",
            valid_from=week_start,
            valid_to=week_end,
            raw_text="Pasta Penne Barilla 2 for 30 kr ord.pris 25 kr/st",
        ),
        Offer(
            id="offer-006",
            store_id="ica-maxi-1004097",
            product_name="Broccoli",
            brand=None,
            category="produce",
            offer_price=15.0,
            original_price=25.0,
            unit="kr/st",
            valid_from=week_start,
            valid_to=week_end,
            raw_text="Broccoli 15 kr/st ord.pris 25 kr/st",
        ),
        Offer(
            id="offer-007",
            store_id="ica-maxi-1004097",
            product_name="Krossade tomater",
            brand="Mutti",
            category="pantry",
            offer_price=12.0,
            original_price=22.0,
            unit="kr/st",
            valid_from=week_start,
            valid_to=week_end,
            raw_text="Krossade tomater Mutti 12 kr/st ord.pris 22 kr/st",
        ),
        Offer(
            id="offer-008",
            store_id="ica-maxi-1004097",
            product_name="Graddfil 12%",
            brand="Arla",
            category="dairy",
            offer_price=16.0,
            original_price=24.0,
            unit="kr/st",
            valid_from=week_start,
            valid_to=week_end,
            raw_text="Graddfil 12% Arla 16 kr/st ord.pris 24 kr/st",
        ),
    ]


async def main():
    print("Initierar databas...")
    await init_db()
    print("Sparar testerbjudanden...")
    offers = make_test_offers()
    await save_offers(offers)
    print(f"Sparat {len(offers)} erbjudanden.")
    print("Klar!")


if __name__ == "__main__":
    asyncio.run(main())
