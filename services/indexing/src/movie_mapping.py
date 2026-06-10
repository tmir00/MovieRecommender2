"""
OpenSearch index mapping for the movie catalog (v4 with field-based lexical + kNN).
"""

MOVIES_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "index": {"knn": True},
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
            "overview": {"type": "text"},
            "tagline": {"type": "text"},
            "pipeline_version": {"type": "keyword"},
            "popularity": {"type": "float"},
            "vote_average": {"type": "float"},
            "vote_count": {"type": "integer"},
            "runtime": {"type": "integer"},
            "original_language": {"type": "keyword"},
            "tmdb_keywords": {"type": "keyword"},
            "tmdb_id": {"type": "integer"},
            "embedding": {
                "type": "knn_vector",
                "dimension": 384,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "lucene",
                },
            },
            "embedding_model": {"type": "keyword"},
            "embedding_text": {"type": "text"},
        }
    },
}
