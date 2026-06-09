"""OpenSearch query helpers."""

from __future__ import annotations

from typing import Any

from opensearchpy import OpenSearch

from config import RecommenderApiConfig
from clients.embedder import EmbedderClient
from shared.features.hit import movie_hit_from_source
from shared.features.constants import LEXICAL_SEARCH_FIELDS
from shared.features.similar_search import build_similar_search_query


def search_movies(client: OpenSearch, config: RecommenderApiConfig, q: str, genre: str | None = None, \
                    year_from: int | None = None, year_to: int | None = None, \
                    size: int = 10) -> list[dict[str, Any]]:
    """
    Search the movie index in OpenSearch using text search and optional filters.
    This is Lexical Search.

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
    # be limited to movies that match the query in LEXICAL_SEARCH_FIELDS.
    if q.strip():
        must.append(
            {
                "multi_match": {
                    "query": q,
                    "fields": LEXICAL_SEARCH_FIELDS,
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

    response = client.search(
        index=config.movies_alias,
        body={"size": size, "query": query},
    )
    return _parse_hits(response)


def _parse_hits(response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Parse OpenSearch hits into movie hit dicts for API responses.

    ============================ Arguments ============================
    response: The OpenSearch response containing the hits.

    ============================ Returns ============================
    List of movie hits with indexed display fields and relevance score.
    """
    return [
        movie_hit_from_source(hit["_source"], hit.get("_score"))
        for hit in response["hits"]["hits"]
    ]


def _resolve_min_vote_count(
    config: RecommenderApiConfig,
    min_vote_count: int | None,
) -> int:
    if min_vote_count is not None:
        return min_vote_count
    return config.similar_min_vote_count


def search_similar_by_vector(client: OpenSearch, config: RecommenderApiConfig, vector: list[float], size: int = 10, \
                            *, genre: str | None = None, min_vote_count: int | None = None) -> list[dict[str, Any]]:
    """
    Find movies nearest to a query vector using OpenSearch kNN search.
    This is (Semantic) Vector Search.

    Do this by:
    1. Checking if the vector dimension matches the expected dimension.
    2. Running kNN inside function_score with optional genre/vote filters.
    3. Parsing the hits from the response and returning a list of dictionaries
    containing the movie ID, title, year, genres, and score.

    ============================ Arguments ============================
    client: The OpenSearch client.
    config: Recommender API configuration with the movies alias.
    vector: Query embedding vector.
    size: Maximum number of neighbors to return.
    genre: Optional exact genre filter.
    min_vote_count: Optional vote floor override; 0 disables the gate.

    ============================ Returns ============================
    Ranked movie hits with similarity scores.
    """
    # Check if the vector dimension matches the expected dimension.
    if len(vector) != config.embedding_dimension:
        raise ValueError(
            f"Vector dimension {len(vector)} does not match "
            f"expected {config.embedding_dimension}"
        )

    # Calculate the maximum number of neighbors to return.
    knn_k = max(size, config.similar_knn_candidates)
    
    query = build_similar_search_query(
        vector,
        knn_k=knn_k,
        genre=genre,
        min_vote_count=_resolve_min_vote_count(config, min_vote_count),
        popularity_factor=config.similar_popularity_factor,
        vote_average_factor=config.similar_vote_average_factor,
    )

    # Execute the search query.
    response = client.search(
        index=config.movies_alias,
        body={"size": size, "query": query},
    )
    # Parse the hits from the response and return a list of dictionaries containing the movie ID, title, year, genres, and score.
    return _parse_hits(response)


def search_similar_by_text(client: OpenSearch, config: RecommenderApiConfig, embedder: EmbedderClient, q: str, size: int = 10, \
                            *, genre: str | None = None, min_vote_count: int | None = None) -> list[dict[str, Any]]:
    """
    Embed query text and run kNN search for similar movies.

    Do this by:
    1. Encoding the query string via the embedder service.
    2. Running kNN search with the resulting vector.

    ============================ Arguments ============================
    client: The OpenSearch client.
    config: Recommender API configuration.
    embedder: Client for the embedder HTTP API.
    q: Free-text query to find semantically similar movies.
    size: Maximum number of neighbors to return.
    genre: Optional exact genre filter.
    min_vote_count: Optional vote floor override; 0 disables the gate.

    ============================ Returns ============================
    Ranked movie hits with similarity scores.
    """
    vectors = embedder.embed_texts([q.strip()])
    return search_similar_by_vector(
        client,
        config,
        vectors[0],
        size=size,
        genre=genre,
        min_vote_count=min_vote_count,
    )


def search_similar_by_movie_id(client: OpenSearch, config: RecommenderApiConfig, embedder: EmbedderClient, movie_id: int, size: int = 10, \
                                *, genre: str | None = None, min_vote_count: int | None = None) -> list[dict[str, Any]]:
    """
    Find movies similar to an indexed movie by its stored embedding.

    Do this by:
    1. Loading the movie document from the movies alias.
    2. Using the stored embedding vector when present.
    3. Falling back to re-embedding embedding_text when the vector is missing.

    ============================ Arguments ============================
    client: The OpenSearch client.
    config: Recommender API configuration.
    embedder: Client for the embedder HTTP API.
    movie_id: Source movie id for neighbor search.
    size: Maximum number of neighbors to return.
    genre: Optional exact genre filter.
    min_vote_count: Optional vote floor override; 0 disables the gate.

    ============================ Returns ============================
    Ranked movie hits excluding the source movie.

    ============================ Raises ============================
    LookupError: When the movie id is not found in the index.
    """
    try:
        # Get the movie document from the movies alias.
        doc = client.get(index=config.movies_alias, id=str(movie_id))
    except Exception as exc:
        raise LookupError(f"Movie with movie_id={movie_id} not found") from exc

    # Get the source of the movie document.
    source = doc["_source"]
    # Get the embedding vector from the movie document.
    vector = source.get("embedding")

    # If the embedding vector is not found, use the embedding text to get the embedding vector.
    if not vector:
        # Get the embedding text from the movie document.
        embedding_text = source.get("embedding_text")
        # If the embedding text is not found, raise a LookupError.
        if not embedding_text:
            raise LookupError(
                f"Movie {movie_id} has no embedding or embedding_text in the index"
            )
        vector = embedder.embed_texts([embedding_text])[0]

    hits = search_similar_by_vector(
        client,
        config,
        vector,
        size=size + 1,
        genre=genre,
        min_vote_count=min_vote_count,
    )
    # Return the hits excluding the source movie.
    return [hit for hit in hits if hit.get("movie_id") != movie_id][:size]


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
