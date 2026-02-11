import json
import threading
import time
from typing import Callable

from kombu import Connection, Consumer, Exchange, Queue, Producer


EXCHANGE_NAME = "reports.events"


def _exchange() -> Exchange:
    return Exchange(EXCHANGE_NAME, type="fanout", durable=True)


def publish_report_event(payload: dict, broker_url: str) -> None:
    exchange = _exchange()
    with Connection(broker_url) as connection:
        producer = Producer(connection)
        producer.publish(
            payload,
            exchange=exchange,
            routing_key="",
            serializer="json",
            retry=True,
            retry_policy={
                "interval_start": 0,
                "interval_step": 1,
                "interval_max": 5,
                "max_retries": 3,
            },
        )


def start_report_event_consumer(
    broker_url: str,
    on_message: Callable[[dict], None],
    stop_event: threading.Event,
) -> None:
    exchange = _exchange()
    while not stop_event.is_set():
        try:
            with Connection(broker_url) as connection:
                queue = Queue(
                    name="",
                    exchange=exchange,
                    routing_key="",
                    exclusive=True,
                    auto_delete=True,
                )

                def _handle(body: dict, message) -> None:
                    try:
                        payload = body if isinstance(body, dict) else json.loads(body)
                        on_message(payload)
                        message.ack()
                    except Exception:
                        message.reject()

                with Consumer(connection, queues=[queue], callbacks=[_handle], accept=["json"]):
                    while not stop_event.is_set():
                        try:
                            connection.drain_events(timeout=1)
                        except Exception:
                            continue
        except Exception:
            time.sleep(2)
