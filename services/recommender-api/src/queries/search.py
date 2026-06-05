"""OpenSearch query helpers."""

from __future__ import annotations

from typing import Any

from opensearchpy import OpenSearch

from config import RecommenderApiConfig


def search_movies(client: OpenSearch, config: RecommenderApiConfig, q: str, genre: str | None = None, \
                    year_from: int | None = None, year_to: int | None = None, \
                    size: int = 10) -> list[dict[str, Any]]:
    """
    Search the movie index in OpenSearch using text search and optional filters.

    The function searches across title-related fields when a non-empty query
    string is provided. Optional genre and year filters can be applied to narrow
    the result set. If no query or filters are provided, the function returns
    movies using a match-all query.

    ============================ Arguments ============================
    client: The OpenSearch client used to execute the search request.
    config: Recommender API configuration containing the movies index alias.
    q: The text query to search for across movie title/search fields.
    genre: Optional genre filter. When provided, only movies matching this genre
        are returned.
    year_from: Optional lower bound for the movie release year, inclusive.
    year_to: Optional upper bound for the movie release year, inclusive.
    size: Maximum number of search results to return.

    ============================= Returns =============================
    A list of dictionaries, where each dictionary contains the movie ID, title,
    release year, genres, and OpenSearch relevance score.
    """
    # Build the search query.
    # The conditions in the "must" list must match for a document to be returned.
    must = []

    # If there is query text after removing whitespace, the returned results will 
    # be limited to the movies that match the query in the title, clean_title, and search_text fields.
    if q.strip():
        must.append(
            {
                "multi_match": {
                    "query": q,
                    "fields": ["title", "clean_title", "search_text"],
                }
            }
        )

    # Build the filter clauses.
    # The conditions in the "filter" list must match for a document to be returned.
    filter_clauses = []
    
    # If a genre is provided, only movies matching this genre are returned.
    if genre:
        filter_clauses.append({"term": {"genres": genre}})
    
    # If a year range is provided, only movies matching this year range are returned.
    if year_from is not None or year_to is not None:
    
        # Build the year range filter.
        year_range = {}
        if year_from is not None:
            year_range["gte"] = year_from
        
        if year_to is not None:
            year_range["lte"] = year_to
        
        # Add the year range filter to the filter clauses.
        filter_clauses.append({"range": {"year": year_range}})

    # If there are any must or filter clauses, build the query.
    if must or filter_clauses:

        # Use bool because we are combining multiple conditions.
        query = {"bool": {}}
        
        # Conceptually, these find movies relevant to the user's query and affect the relevance score.
        if must:
            query["bool"]["must"] = must
        
        # Conceptually, these narrow the matching movies by exact constraints like genre and year,
        # without affecting the relevance score (used to rank the results).
        if filter_clauses:
            query["bool"]["filter"] = filter_clauses
    
    # If there are no must or filter clauses, return all movies.
    else:
        query = {"match_all": {}}

    # Execute the search query.
    response = client.search(
        index=config.movies_alias,
        body={"size": size, "query": query},
    )

    # Extract the results from the response and store them in a list.
    results = []
    # Iterate over the hits in the response.
    for hit in response["hits"]["hits"]:
        # Get the source of the hit.
        source = hit["_source"]
        # Append the movie ID, title, year, genres, and score to the results list.
        results.append(
            {
                "movie_id": source.get("movie_id"),
                "title": source.get("title"),
                "year": source.get("year"),
                "genres": source.get("genres", []),
                "score": hit.get("_score"),
            }
        )
    return results


def opensearch_ready(client: OpenSearch, config: RecommenderApiConfig) -> bool:
    """
    ! Health check function.

    Check whether OpenSearch is reachable and the movie search index is ready.

    The function first verifies that the OpenSearch cluster responds to a ping.
    It then checks whether the configured movies alias exists. This is useful
    for health checks because the API should only be considered ready when it
    can connect to OpenSearch and query the expected movie index alias.

    ============================ Arguments ============================
    client: The OpenSearch client used to check cluster availability.
    config: Recommender API configuration containing the movies index alias.

    ============================= Returns =============================
    True if OpenSearch is reachable and the movies alias exists; otherwise False.
    """
    try:
        if not client.ping():
            return False
        return client.indices.exists_alias(name=config.movies_alias)
    except Exception:
        return False
