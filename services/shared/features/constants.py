"""
Shared constants for movie search and indexing.

Search code should import LEXICAL_SEARCH_FIELDS instead of hardcoding field names
so lexical queries stay aligned with the indexed document shape.
"""

from __future__ import annotations

# GET /search uses multi_match only (no popularity/rating boosts).
# GET /search/similar uses kNN + function_score — see similar_search.py.
LEXICAL_SEARCH_FIELDS = [
    "title^3",
    "clean_title^2",
    "tagline^1.5",
    "overview^1",
    "tmdb_keywords^1",
]
