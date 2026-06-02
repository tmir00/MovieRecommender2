"""Rating event producer — streams MovieLens rating events to Kafka."""

from __future__ import annotations

import json
import os
import time
import pandas as pd

from confluent_kafka import Producer
from helpers.event_builders import EVENT_BUILDERS
from shared.logging_config import configure_logging


# Configure logging.
logger = configure_logging(os.environ.get("LOGGER_NAME", "dataset-producer"))


def _delivery_report(err, msg) -> None:
    """
    Callback function to handle the delivery report of a rating event.
    
    ==================== Arguments ====================
    err: The error object if the delivery failed, otherwise None.
    msg: The delivery report object.
    ==================== Returns ====================
    None
    """
    # If there is an error, log the error and return.
    if err is not None:
        logger.error(
            "Failed to deliver rating event",
            extra={"error": str(err)},
        )
        return

    # If the delivery was successful, log the event.
    logger.debug(
        "Delivered rating event",
        extra={
            "topic": msg.topic(),
            "partition": msg.partition(),
            "offset": msg.offset(),
        },
    )


def main() -> None:
    """Main function to run the ratings producer."""

    # Load in the necessary environment variables.
    max_events = int(os.environ.get("MAX_EVENTS", "0"))
    log_every_n_events = int(os.environ.get("LOG_EVERY_N_EVENTS", "1000"))
    stream_delay_seconds = float(os.environ.get("STREAM_DELAY_SECONDS", "0"))
    CHUNK_SIZE = int(os.environ.get("CSV_CHUNK_SIZE", "100_000"))

    try:
        bootstrap = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
        dataset_type = os.environ["DATASET_TYPE"]  # ratings or tags
        csv_path = os.environ["CSV_PATH"]
        topic = os.environ["KAFKA_TOPIC"]
        event_builder = EVENT_BUILDERS[dataset_type]
    except KeyError as exc:
        logger.critical(
            "Missing required environment variable",
            extra={"missing_env_var": str(exc)},
        )
        raise

    # Create a Kafka producer.
    producer = Producer({"bootstrap.servers": bootstrap})
    # Log the producer creation.
    logger.info(
        "Starting ratings producer",
        extra={
            "bootstrap_servers": bootstrap,
            "dataset_type": dataset_type,
            "topic": topic,
            "ratings_csv_path": csv_path,
            "max_events": max_events,
            "log_every_n_events": log_every_n_events,
            "stream_delay_seconds": stream_delay_seconds,
        },
    )

    # Read the ratings CSV file
    events_sent = 0
    events_read = 0
    for chunk in pd.read_csv(csv_path, chunksize=CHUNK_SIZE):

        # If we've reached the max number of events, stop the producer.
        if max_events > 0 and events_sent >= max_events:
                logger.info("Reached max events. Stopping producer")
                break

        # Go through each row in the ratings CSV file.
        for row in chunk.itertuples(index=False):

            # If we've reached the max number of events, stop the producer.
            if max_events > 0 and events_sent >= max_events:
                logger.info("Reached max events. Stopping producer")
                break

            events_read += 1

            # Try to create an event for the rating.
            # If the row is malformed, log the error and skip the row.
            try:
                event, key = event_builder(row)
            except Exception:
                logger.exception(
                    f"Failed to build {dataset_type} event from row",
                    extra={"row_index": events_read},
                )
                continue

            # Use the Kafka producer to send the event to the topic.
            # If the queue is full, log the error and continue.
            try:
                producer.produce(
                    topic=topic,
                    key=key,
                    value=json.dumps(event).encode("utf-8"),
                    callback=_delivery_report,
                )
            except BufferError:
                logger.exception("Kafka producer queue is full")
                producer.poll(1)
                continue

            # Process any delivery callbacks that are ready.
            producer.poll(0)
            events_sent += 1

            # Log every n events.
            if events_sent % log_every_n_events == 0:
                logger.info(
                    "Queued rating events",
                    extra={
                        "events_sent": events_sent,
                        "topic": topic,
                    },
                )

            # Wait for the stream delay.
            if stream_delay_seconds > 0:
                time.sleep(stream_delay_seconds)

        if max_events > 0 and events_sent >= max_events:
            break

    # Wait for all queued messages to be delivered or fail.
    logger.info("Finished reading CSV. Flushing queued Kafka messages")
    producer.flush()
    logger.info(
        "Finished streaming rating events",
        extra={
            "events_read": events_read,
            "events_sent": events_sent,
            "topic": topic,
        },
    )


if __name__ == "__main__":
    main()
