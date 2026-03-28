"""Tests for ICA Maxi scraper parsing functions."""

from backend.scrapers.ica_maxi import (
    classify_category,
    parse_price,
    parse_original_price,
    parse_max_per_household,
    parse_membership,
)


def test_classify_category_meat():
    assert classify_category("Kycklingfilé") == "meat"
    assert classify_category("Nötfärs") == "meat"
    assert classify_category("Falukorv") == "meat"


def test_classify_category_fish():
    assert classify_category("Laxfilé") == "fish"
    assert classify_category("Torskfilé") == "fish"


def test_classify_category_dairy():
    assert classify_category("Yoghurt Naturell") == "dairy"
    assert classify_category("Mellanmjölk") == "dairy"


def test_classify_category_produce():
    assert classify_category("Tomat") == "produce"
    assert classify_category("Broccoli") == "produce"


def test_classify_category_other():
    assert classify_category("Okänd produkt XYZ") == "other"


def test_parse_price_multi_buy():
    price, deal, unit = parse_price("2 för 85 kr")
    assert price == 42.5
    assert deal == "2 för 85 kr"
    assert unit == "kr/st"


def test_parse_price_per_kg():
    price, deal, unit = parse_price("89 kr/kg")
    assert price == 89.0
    assert deal is None
    assert unit == "kr/kg"


def test_parse_price_per_st():
    price, deal, unit = parse_price("40 kr/st")
    assert price == 40.0
    assert unit == "kr/st"


def test_parse_price_plain():
    price, deal, unit = parse_price("35 kr")
    assert price == 35.0
    assert unit == "kr/st"


def test_parse_price_colon_format():
    """Handle "39:-" format."""
    price, deal, unit = parse_price("39:- kr")
    assert price == 39.0


def test_parse_original_price():
    assert parse_original_price("Ord.pris 54:95 kr") == 54.95
    assert parse_original_price("Ord.pris 50:11-54:95 kr") == 54.95  # Takes highest
    assert parse_original_price("Ingen pris info") is None


def test_parse_max_per_household():
    assert parse_max_per_household("Max 2 köp/hushåll") == 2
    assert parse_max_per_household("Max 1 köp/hushåll") == 1
    assert parse_max_per_household("Ingen begränsning") is None


def test_parse_membership():
    assert parse_membership("Stammispris") is True
    assert parse_membership("Medlemspris") is True
    assert parse_membership("Ordinarie pris") is False
