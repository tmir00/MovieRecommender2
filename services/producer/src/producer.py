"""Rating event producer — connects to Kafka and sends a startup test message."""

from __future__ import annotations

import json
import os
import sys

from confluent_kafka import Producer


def _delivery_report(err, msg) -> None:
    if err is not None:
        print(f"Delivery failed: {err}", file=sys.stderr)
        return
    print(
        f"Delivered to {msg.topic()} "
        f"[partition {msg.partition()}] @ offset {msg.offset()}"
    )


def main() -> None:
    bootstrap = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
    topic = os.environ.get("KAFKA_TOPIC", "ratings")

    producer = Producer({"bootstrap.servers": bootstrap})

    event = {
        "event_type": "rating.created",
        "user_id": 1,
        "movie_id": 1,
        "rating": 4.0,
        "timestamp": 0,
    }

    producer.produce(
        topic=topic,
        key=str(event["user_id"]),
        value=json.dumps(event).encode("utf-8"),
        callback=_delivery_report,
    )
    producer.flush()
    print(f"Producer ready (bootstrap={bootstrap}, topic={topic})")


if __name__ == "__main__":
    main()
