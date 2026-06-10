"""Seed catalog_movies from MovieLens movies.csv and links.csv."""

from __future__ import annotations

import os
import sys
import logging

import pandas as pd

from config import IndexingConfig
from shared.db.catalog import upsert_catalog_movies_batch
from shared.db.engine import create_engine_from_url
from shared.features.adapters.csv import load_links_index, row_to_catalog_input
from shared.features.parsers import parse_title_year, resolve_year
from shared.logging_config import configure_logging


def seed_catalog(config: IndexingConfig, logger: logging.Logger) -> dict[str, int]:
    """
    Load ML-25m movies into catalog_movies from CSV files.

    Do this by:
    1. Reading movies.csv in chunks.
    2. Joining tmdb_id from links.csv via row_to_catalog_input.
    3. Upserting batches into Postgres without touching TMDB columns on conflict.

    ============================ Arguments ============================
    config: Indexing configuration with CSV paths and pipeline version.
    logger: Logger for progress output.

    ============================ Returns ============================
    Counts for rows_read and rows_upserted.
    """
    # Create the SQLAlchemy engine from the database URL.
    engine = create_engine_from_url(config.database_url)
    # Load the links index from the links CSV file.
    links_index = load_links_index(config.links_csv_path)

    rows_read = 0
    rows_upserted = 0
    batch = []

    # Read the movies CSV file in chunks.
    for chunk in pd.read_csv(config.movies_csv_path, chunksize=config.bulk_chunk_size):
        # Iterate over the rows in the chunk.
        for row in chunk.itertuples(index=False):
            # If the maximum number of movies has been reached, break.
            if config.max_movies > 0 and rows_read >= config.max_movies:
                break

            # Convert the row to a catalog input.
            catalog_input = row_to_catalog_input(row, links_index)
            # Parse the title and year.
            _, parsed_year = parse_title_year(catalog_input.title)
            # Resolve the year.
            year = resolve_year(catalog_input.title, parsed_year)

            # Add the row to the batch to be upserted.
            batch.append(
                {
                    "movie_id": catalog_input.movie_id,
                    "title": catalog_input.title,
                    "genres": catalog_input.genres,
                    "year": year,
                    "tmdb_id": catalog_input.tmdb_id,
                }
            )
            rows_read += 1

            # If the batch size has been reached, upsert the batch.
            if len(batch) >= config.bulk_chunk_size:
                # Upsert the batch.
                rows_upserted += upsert_catalog_movies_batch(
                    engine,
                    batch,
                    pipeline_version=config.pipeline_version,
                )
                # Clear the batch so that we can start a new batch.
                batch.clear()

                # If the number of rows upserted has been reached, log the progress.
                if rows_upserted % config.log_every_n_docs == 0:
                    # Log the progress.
                    logger.info(
                        "Seed catalog progress",
                        extra={
                            "rows_read": rows_read,
                            "rows_upserted": rows_upserted,
                        },
                    )

        # If the maximum number of movies has been reached, break.
        if config.max_movies > 0 and rows_read >= config.max_movies:
            break

    # If there are any rows left in the batch, upsert them.
    if batch:
        rows_upserted += upsert_catalog_movies_batch(
            engine,
            batch,
            pipeline_version=config.pipeline_version,
        )

    # Return the counts of rows read and upserted.
    return {"rows_read": rows_read, "rows_upserted": rows_upserted}


def main() -> None:
    """
    Run the catalog seed job.

    ============================ Returns ============================
    None
    """
    # Configure logging and load the configuration.
    logger = configure_logging(os.environ.get("LOGGER_NAME", "movie-indexer"))
    config = IndexingConfig.from_env()

    # Log the start of the catalog seed job.
    logger.info(
        "Starting catalog seed",
        extra={
            "movies_csv_path": config.movies_csv_path,
            "links_csv_path": config.links_csv_path,
            "pipeline_version": config.pipeline_version,
        },
    )

    # Seed the catalog.
    summary = seed_catalog(config, logger)
    # Log the completion of the catalog seed job.
    logger.info("Catalog seed completed", extra=summary)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.getLogger(os.environ.get("LOGGER_NAME", "movie-indexer")).exception(
            "Catalog seed failed"
        )
        sys.exit(1)
