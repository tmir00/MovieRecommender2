import pandas as pd

from typing import Tuple

def build_rating_event(row: pd.Series) -> Tuple[dict, str]:
    """
    Build a rating event from a row of the ratings CSV file.

    ==================== Arguments ====================
    row: A row of the ratings CSV file.

    ===================== Returns =====================
    A tuple containing the rating event and the Kafka message key.
    The key is the user ID, which helps Kafka route all events for
    the same user to the same partition. This preserves ordering for
    that user's events within the topic.
    """
    return {
        "event_type": "rating.created",
        "user_id": int(row.userId),
        "movie_id": int(row.movieId),
        "rating": float(row.rating),
        "timestamp": int(row.timestamp),
    }, str(row.userId)


def build_tag_event(row: pd.Series) -> Tuple[dict, str]:
    """
    Build a tag event from a row of the tags CSV file.

    ==================== Arguments ====================
    row: A row of the tags CSV file.

    ===================== Returns =====================
    A tuple containing the tag event and the Kafka message key.
    The key is the user ID, which helps Kafka route all events for
    the same user to the same partition. This preserves ordering for
    that user's events within the topic.
    """
    return {
        "event_type": "tag.created",
        "user_id": int(row.userId),
        "movie_id": int(row.movieId),
        "tag": row.tag,
        "timestamp": int(row.timestamp),
    }, str(row.userId)


EVENT_BUILDERS = {
    "ratings": build_rating_event,
    "tags": build_tag_event,
}