"""OpenSearch query builder for vector similarity search (shared by API and smoke tests)."""

from __future__ import annotations

from typing import Any

DEFAULT_SIMILAR_POPULARITY_FACTOR = 0.05
DEFAULT_SIMILAR_VOTE_AVERAGE_FACTOR = 0.1


def build_similar_search_query(vector: list[float], *, knn_k: int, genre: str | None = None, \
                    min_vote_count: int = 0, popularity_factor: float = DEFAULT_SIMILAR_POPULARITY_FACTOR, \
                    vote_average_factor: float = DEFAULT_SIMILAR_VOTE_AVERAGE_FACTOR) -> dict[str, Any]:
    """
    Build a kNN query wrapped in function_score for popularity/rating boosts.

    Lexical GET /search does not use these boosts; only GET /search/similar does.

    ============================ Arguments ============================
    vector: Query embedding vector.
    knn_k: Number of vector neighbors to retrieve before reranking.
    genre: Optional exact genre filter.
    min_vote_count: Vote floor; 0 disables the gate. Docs missing vote_count pass.
    popularity_factor: field_value_factor weight for popularity (log1p).
    vote_average_factor: field_value_factor weight for vote_average.

    ============================ Returns ============================
    OpenSearch query body fragment for the ``query`` key.
    """
    # Initialize a list to store the things to filter by.
    filter_clauses = []

    # If a genre is provided, add a filter to the query to only return movies with that genre.
    if genre:
        filter_clauses.append({"term": {"genres": genre}})

    # If a minimum vote count is provided, add a filter to the query to only return movies with that vote count.
    if min_vote_count > 0:
        filter_clauses.append(
            {
                "bool": {
                    "should": [
                        {"range": {"vote_count": {"gte": min_vote_count}}},
                        {"bool": {"must_not": {"exists": {"field": "vote_count"}}}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    # Build the kNN query. This is the query to find the nearest neighbors to the query vector.
    knn_query: dict[str, Any] = {
        "knn": {
            "embedding": {
                "vector": vector,
                "k": knn_k,
            }
        }
    }

    # If there are any filter clauses, add them to the query.
    if filter_clauses:
        # Build the base query. This is the query to find the nearest neighbors to the query vector.
        base_query = {
            "bool": {
                "must": [knn_query],
                "filter": filter_clauses,
            }
        }
    else:
        base_query = knn_query

    return {
        "function_score": {
            "query": base_query,
            "functions": [
                {
                    "field_value_factor": {
                        "field": "popularity",
                        "factor": popularity_factor,
                        "modifier": "log1p", # Squish large popularity values so they don't dominate the score.
                        "missing": 1.0,
                    }
                },
                {
                    "field_value_factor": {
                        "field": "vote_average",
                        "factor": vote_average_factor,
                        "modifier": "none",
                        "missing": 0,
                    }
                },
            ],
            "score_mode": "sum",
            "boost_mode": "sum",
        }
    }
