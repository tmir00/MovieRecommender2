"""
OpenSearch index mapping for the movie catalog.

Vector search: add a knn_vector field in a future mapping version when embedding
models are wired in.
"""

MOVIES_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
    },
    "mappings": {
        "properties": {
            "movie_id": {"type": "integer"},
            "title": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "clean_title": {"type": "text"},
            "year": {"type": "integer"},
            "genres": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "search_text": {"type": "text"},
            "pipeline_version": {"type": "keyword"},
        }
    },
}
