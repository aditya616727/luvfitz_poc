"""
Taxonomy mapping utilities – maps product names/descriptions to
Google's standard Product Taxonomy (2021-09-21) for SEO.

Reference: https://www.google.com/basepages/producttype/taxonomy.en-US.txt
"""

import json
import os
from typing import Optional
from app.core.logging import logger

# ── Load Google taxonomy rules ──────────────────────────────────
_TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), "google_taxonomy.json")

with open(_TAXONOMY_PATH, "r") as f:
    _TAXONOMY_DATA = json.load(f)

TAXONOMY_RULES: list[dict] = _TAXONOMY_DATA["rules"]
FALLBACK_TAXONOMY: dict = _TAXONOMY_DATA["fallback_taxonomy"]
STYLE_KEYWORDS: dict[str, list[str]] = _TAXONOMY_DATA["style_keywords"]

# Also keep the old rules file around for backward compat if needed
_OLD_RULES_PATH = os.path.join(os.path.dirname(__file__), "taxonomy_rules.json")
if os.path.exists(_OLD_RULES_PATH):
    with open(_OLD_RULES_PATH, "r") as f:
        _OLD_RULES = json.load(f)
else:
    _OLD_RULES = None


def map_taxonomy(
    name: str, description: str = ""
) -> tuple[Optional[str], Optional[str]]:
    """
    Returns (internal_category, google_product_category) for a product.

    The google_product_category is the *exact* path from Google's standard
    apparel taxonomy (2021-09-21), e.g.:
        "Apparel & Accessories > Clothing > Shirts & Tops"

    Returns (None, None) if no keyword matches.
    """
    text = f"{name} {description}".lower()

    for rule in TAXONOMY_RULES:
        for kw in rule["keywords"]:
            if kw in text:
                return rule["category"], rule["google_taxonomy"]

    logger.warning(f"No taxonomy match for: {name}")
    return None, None


def get_google_taxonomy_id(
    name: str, description: str = ""
) -> Optional[int]:
    """
    Returns the Google taxonomy numeric ID for a product, or None.
    """
    text = f"{name} {description}".lower()
    for rule in TAXONOMY_RULES:
        for kw in rule["keywords"]:
            if kw in text:
                return rule.get("google_taxonomy_id")
    return None


def get_fallback_google_taxonomy(
    category: str,
) -> tuple[str, Optional[int]]:
    """
    Returns (google_taxonomy_path, google_taxonomy_id) for a given
    internal category when keyword matching fails.
    """
    fb = FALLBACK_TAXONOMY.get(category, {})
    return fb.get("google_taxonomy", "Apparel & Accessories"), fb.get("google_taxonomy_id")


def extract_style_tags(name: str, description: str = "", color: str = "") -> list[str]:
    """
    Extract style/vibe tags from product text.
    """
    text = f"{name} {description} {color}".lower()
    tags: list[str] = []

    for style, keywords in STYLE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                tags.append(style)
                break  # one match per style is enough

    # Fallback tag
    if not tags:
        tags.append("casual")

    return tags
