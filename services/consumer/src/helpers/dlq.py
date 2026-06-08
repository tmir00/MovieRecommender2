"""Dead letter queue persistence for failed Kafka messages."""

import base64
import json
from typing import Any

from confluent_kafka import Message
from sqlalchemy import Connection

from shared.db.events import insert_dead_letter_event


def message_payload_text(msg: Message) -> str:
    """
    Return the Kafka message body as text for storage in the DLQ.

    Uses UTF-8 when possible; falls back to base64 for binary payloads.
    """
    raw = msg.value()
    if raw is None:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return base64.b64encode(raw).decode("ascii")


def payload_to_text(payload: Any) -> str:
    """Serialize a parsed payload dict back to JSON for the DLQ."""
    return json.dumps(payload, default=str)


def persist_dead_letter_event(
    connection: Connection,
    *,
    msg: Message,
    consumer_group: str,
    error_type: str,
    error_message: str,
    payload: str | None = None,
) -> None:
    """
    Insert one failed message into dead_letter_events.

    ==================== Arguments ====================
    connection: Active SQLAlchemy Core connection.
    msg: The Kafka message that failed processing.
    consumer_group: Consumer group id (for tracing which reader failed).
    error_type: Short category (e.g. json_decode_error, validation_error).
    error_message: Human-readable error detail.
    payload: Raw or serialized message body (defaults to msg value as text).
    """
    if payload is None:
        payload = message_payload_text(msg)

    insert_dead_letter_event(
        connection,
        source_topic=msg.topic(),
        source_partition=msg.partition(),
        source_offset=msg.offset(),
        consumer_group=consumer_group,
        error_type=error_type,
        error_message=error_message,
        payload=payload,
    )
