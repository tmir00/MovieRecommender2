"""Decode, validate, and persist a single Kafka message."""

from __future__ import annotations

import json
import logging
from enum import Enum
from dataclasses import dataclass

from config import ConsumerConfig
from pydantic import ValidationError
from sqlalchemy.engine import Engine
from confluent_kafka import Consumer, KafkaError, Message
from helpers.dlq import message_payload_text, payload_to_text, persist_dead_letter_event


class ProcessResult(Enum):
    """
    Outcome of handling one Kafka message.
    This is used to determine the next action to take in the message pipeline.
    Use ENUM so that we set a controlled set of possible outcomes.
    
    If outcome is OK, the message has been successfully processed and the offset has been committed.
    If outcome is SENT_TO_DLQ, the message has been sent to the dead letter queue and the offset has been committed.
    If outcome is DLQ_FAILED, the message has not been sent to the dead letter queue and the offset has not been committed.
    """

    OK = "ok"
    SENT_TO_DLQ = "sent_to_dlq"
    DLQ_FAILED = "dlq_failed"


@dataclass
class ConsumerContext:
    """
    Context object to store the engine, consumer, and configuration for the consumer.
    
    This is used to pass consumer data to the message pipeline.
    """

    engine: Engine
    consumer: Consumer
    config: ConsumerConfig
    logger: logging.Logger


def message_log_extra(msg: Message) -> dict[str, object]:
    """ Extract useful Kafka metadata for logging."""
    
    return {
        "topic": msg.topic(),
        "partition": msg.partition(),
        "offset": msg.offset(),
    }


def poll_message(consumer: Consumer, logger: logging.Logger) -> Message | None:
    """
    Poll Kafka for the next message.

    Returns None when there is nothing to process or the error is ignorable
    (e.g. partition EOF while caught up).
    """
    # Poll the Kafka consumer for the next message.
    msg = consumer.poll(1.0)
    
    # If there is no message, return None.
    if msg is None:
        return None

    # If there is an error, log the error and return None.
    if msg.error():
        if msg.error().code() == KafkaError._PARTITION_EOF:
            return None
        logger.error(
            "Kafka consumer error",
            extra={"error": str(msg.error())},
        )
        return None

    return msg


def send_to_dlq_and_commit(ctx: ConsumerContext, msg: Message, error_type: str, error_message: str, payload: str | None = None) -> bool:
    """
    Write a failed message to Postgres in a DLQ and commit its Kafka offset.
    
    ==================== Arguments ====================
    ctx: The consumer context object.
    msg: The Kafka message that failed processing.
    error_type: The type of error that occurred.
    error_message: The human-readable error message.
    payload: The raw or serialized message body.

    ===================== Returns =====================
    True if stored and committed; False if DLQ write failed (offset not committed).
    """
    # Try to write the failed message to the DLQ and commit the offset.
    try:
        # Begin a new database connection.
        with ctx.engine.begin() as connection:
            # Write the failed message to the DLQ.
            persist_dead_letter_event(
                connection,
                msg=msg,
                consumer_group=ctx.config.group_id,
                error_type=error_type,
                error_message=error_message,
                payload=payload,
            )
        # Commit the offset.
        ctx.consumer.commit(message=msg, asynchronous=False)
        # Return True if the message was written to the DLQ and the offset was committed.
        return True
    
    except Exception:
        # Log the failure and return False if the message was not written to the DLQ and the offset was not committed.
        ctx.logger.exception(
            "Failed to write dead letter event",
            extra={**message_log_extra(msg), "error_type": error_type},
        )
        return False


def fail_message(ctx: ConsumerContext, msg: Message, log_message: str, error_type: str, error_message: str, payload: str | None = None) -> ProcessResult:
    """
    Log the failure, store the message in the DLQ, and return the outcome.
    
    ==================== Arguments ====================
    ctx: The consumer context object.
    msg: The Kafka message that failed processing.
    log_message: The message to log.
    error_type: The type of error that occurred.
    error_message: The human-readable error message.
    payload: The raw or serialized message body.

    ===================== Returns =====================
    The outcome of the message processing.
    If the message was sent to the dead letter queue successfully, return ProcessResult.SENT_TO_DLQ.
    If the message was not sent to the dead letter queue, return ProcessResult.DLQ_FAILED.
    """
    # Log the failure.
    ctx.logger.exception(log_message, extra=message_log_extra(msg))
    if send_to_dlq_and_commit(ctx, msg, error_type=error_type, error_message=error_message, payload=payload):
        return ProcessResult.SENT_TO_DLQ

    # If the message was not sent to the dead letter queue, return ProcessResult.DLQ_FAILED.
    ctx.logger.error(log_message, extra=message_log_extra(msg))

    return ProcessResult.DLQ_FAILED


def process_message(msg: Message, ctx: ConsumerContext) -> ProcessResult:
    """
    Run decode → validate → persist for one Kafka message.

    ==================== Returns ====================
    OK on success, SENT_TO_DLQ if stored as dead letter, DLQ_FAILED if DLQ write failed.
    """
    # Get the configuration for the consumer.
    config = ctx.config

    try:
        # Decode the message payload as JSON.
        raw_payload = json.loads(msg.value().decode("utf-8"))
    
    # If the message payload is not valid JSON, fail the message.
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        # Log the failure and send the message to the dead letter queue.
        return fail_message(
            ctx,
            msg,
            log_message="Failed to decode Kafka message as JSON",
            error_type="json_decode_error",
            error_message=str(exc),
            payload=message_payload_text(msg),
        )


    # Validate the message payload against the event schema.
    try:
        # Validate the message payload against the event schema.
        event = config.event_schema.model_validate(raw_payload)
    
    except ValidationError as exc:
        # Log the failure and send the message to the dead letter queue.
        return fail_message(
            ctx,
            msg,
            log_message=f"Invalid {config.dataset_type} event payload",
            error_type="validation_error",
            error_message=str(exc),
            payload=payload_to_text(raw_payload),
        )


    # Try to persist the event to the database.
    try:
        # Begin a new database connection.
        with ctx.engine.begin() as connection:
            # Persist the event to the database.
            config.persist_event(
                connection,
                event,
                pipeline_version=config.pipeline_version,
            )
    
    # If the event cannot be persisted, fail the message.
    except Exception as exc:
        # Log the failure and send the message to the dead letter queue.
        return fail_message(
            ctx,
            msg,
            log_message=f"Failed to persist {config.dataset_type} event",
            error_type="persistence_error",
            error_message=str(exc),
            payload=event.model_dump_json(),
        )

    return ProcessResult.OK
