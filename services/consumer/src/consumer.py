"""Dataset event consumer — reads Kafka events and persists them to Postgres."""

from __future__ import annotations

import os
import signal

from confluent_kafka import Consumer

from config import ConsumerConfig
from db.session import get_engine
from health.app import create_health_app
from health.server import start_health_server
from health.state import HealthState
from message_pipeline import (
    ConsumerContext,
    ProcessResult,
    poll_message,
    process_message,
)
from shared.logging_config import configure_logging


# Configure logging.
logger = configure_logging(os.environ.get("LOGGER_NAME", "dataset-consumer"))


def main() -> None:
    """Main function to run the dataset consumer."""

    # Load in the settings for this consumer instance from the environment variables.
    try:
        config = ConsumerConfig.from_env()
    
    # IF a required environment variable is missing, log the error and raise an exception.
    except KeyError as exc:
        logger.critical(
            "Missing required environment variable",
            extra={"missing_env_var": str(exc)},
        )
        raise

    # Create a SQLAlchemy engine to connect to the database and allow our code to interact with the database.
    engine = get_engine()

    # Shared health state for Kubernetes-style liveness/readiness probes (HTTP side thread).
    health_state = HealthState()

    # Start the HTTP health server on a background thread (maps to K8s liveness/readiness probes).
    health_app = create_health_app(health_state, engine)
    start_health_server(health_app)

    # Create a Kafka consumer to subscribe to the topic and read the messages.
    consumer = Consumer(
        {
            "bootstrap.servers": config.bootstrap_address,
            "group.id": config.group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([config.topic])
    # Attach the consumer to the health state so that the health server can check if the consumer is still alive.
    health_state.set_consumer(consumer)

    # Create a context object to store Consumer Information.
    ctx = ConsumerContext(
        engine=engine,
        consumer=consumer,
        config=config,
        logger=logger,
    )

    # Set up a signal handler to request a graceful shutdown of the consumer.
    # Let the health server detect the shutdown and update the liveness/readiness probes.
    def _request_shutdown(signum: int, _frame) -> None:
        health_state.set_shutting_down()
        logger.info("Shutdown requested", extra={"signal": signum})

    signal.signal(signal.SIGTERM, _request_shutdown)
    signal.signal(signal.SIGINT, _request_shutdown)

    logger.info("Starting dataset consumer", extra=config.startup_log_extra())

    events_processed = 0
    events_invalid = 0

    # Start the consumer so that it continues to poll for messages until the consumer is interrupted.
    try:
        while not health_state.is_shutting_down():
            # Heartbeat for liveness probes — updated every loop turn, even when the topic is quiet.
            health_state.touch_poll()

            # If we've reached the max number of events, stop the consumer.
            if config.max_events > 0 and events_processed >= config.max_events:
                logger.info("Reached max events. Stopping consumer")
                break

            # Poll the Kafka consumer for the next message.
            msg = poll_message(consumer, logger)
            # If there is no message, continue to the next iteration of the loop.
            if msg is None:
                continue

            # Process the message.
            result = process_message(msg, ctx)

            # If the message was processed successfully, commit the offset.
            if result == ProcessResult.OK:
                consumer.commit(message=msg, asynchronous=False)
                events_processed += 1
                health_state.touch_success()

                # If we've processed enough events, log the progress.
                if events_processed % config.log_every_n_events == 0:
                    logger.info(
                        "Persisted events",
                        extra={
                            "events_processed": events_processed,
                            "topic": config.topic,
                        },
                    )

            # If the message was sent to the dead letter queue, increment the invalid counter.
            elif result == ProcessResult.SENT_TO_DLQ:
                events_invalid += 1

            # else: DLQ_FAILED: offset not committed — Kafka will redeliver.

    # If the consumer is interrupted by the user, log the interruption.
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")

    # On exit, close the consumer and log the exit.
    finally:
        consumer.close()
        logger.info(
            "Stopped dataset consumer",
            extra={
                "events_processed": events_processed,
                "events_invalid": events_invalid,
                "topic": config.topic,
            },
        )


if __name__ == "__main__":
    main()
