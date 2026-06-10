"""Helpers for OpenSearch bulk indexing and Postgres sync marking."""

from __future__ import annotations

import logging
from typing import Any

from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk


def failed_movie_ids_from_bulk_errors(errors: list[Any]) -> set[int]:
    """
    Parse opensearchpy bulk error items into failed movie document ids.

    ============================ Arguments ============================
    errors: Error list returned by opensearchpy.helpers.bulk when
        raise_on_error=False.

    ============================ Returns ============================
    Set of movie_id values whose bulk action failed.
    """
    failed = set()

    # For each error item, parse the opensearchpy bulk error items into failed movie document ids.
    for item in errors:
        # If the item is not a dictionary, skip it.
        if not isinstance(item, dict):
            continue

        # For each operation type, parse the opensearchpy bulk error items into failed movie document ids.
        for op_name in ("index", "create", "update"):
            # Get the operation from the item.
            op = item.get(op_name)
            # If the operation is not a dictionary, skip it.
            if not isinstance(op, dict):
                continue

            # Get the document ID from the operation.
            doc_id = op.get("_id")
            # If the document ID is not found, skip it.
            if doc_id is None:
                continue

            # Add the document ID to the failed set.
            failed.add(int(doc_id))
            # Break out of the loop after finding the first operation type that has a document ID.
            break

    return failed


def successful_movie_ids(batch_ids: list[int], failed_ids: set[int]) -> list[int]:
    """
    Return movie ids from a batch whose bulk actions succeeded.

    ============================ Arguments ============================
    batch_ids: movie_id values sent in the bulk batch.
    failed_ids: movie_id values reported as failed by bulk().

    ============================ Returns ============================
    movie_id list preserving batch order for successful items only.
    """
    # Return the movie IDs from the batch that are not in the failed set.
    return [movie_id for movie_id in batch_ids if movie_id not in failed_ids]


def flush_bulk_batch(client: OpenSearch, batch: list[dict[str, Any]], logger: logging.Logger, *, log_context: str) -> tuple[int, set[int]]:
    """
    Send one bulk batch to OpenSearch and return failure count and failed ids.

    ============================ Arguments ============================
    client: The OpenSearch client.
    batch: Bulk action dicts for OpenSearch.
    logger: Logger for partial-failure errors.
    log_context: Short label for log messages (e.g. job name).

    ============================ Returns ============================
    Tuple of (failure_count, failed_movie_ids).
    """
    # Send the bulk batch to the OpenSearch cluster.
    _success, errors = bulk(
        client,
        batch,
        raise_on_error=False,
        raise_on_exception=False,
    )

    # Parse the bulk errors into failed movie document ids.
    failed_ids = failed_movie_ids_from_bulk_errors(errors or [])
    # Get the number of failed movie document ids.
    failure_count = len(failed_ids)
    
    # If there are any failures, log the errors.
    if failure_count:
        logger.error(
            f"{log_context} bulk batch had failures",
            extra={
                "failure_count": failure_count,
                "failed_movie_ids": sorted(failed_ids)[:20],
            },
        )

    return failure_count, failed_ids
