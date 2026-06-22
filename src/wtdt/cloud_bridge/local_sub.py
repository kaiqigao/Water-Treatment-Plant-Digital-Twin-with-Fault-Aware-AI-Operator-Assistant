import json
from collections.abc import Callable
from dataclasses import dataclass
from time import time
from typing import Any

from wtdt.messaging.topics import CLOUD_TAG_TOPIC_PREFIX

TagHandler = Callable[[str, float, float], None]


@dataclass
class LocalTagSubscriber:
    host: str
    port: int
    on_tag: TagHandler
    client_id: str = "wtdt-cloud-bridge-local"

    def __post_init__(self) -> None:
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError("paho-mqtt is required for the cloud bridge") from exc

        self._mqtt = mqtt
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id)
        self.client.on_message = self._on_message
        self.received = 0
        self.dropped = 0

    @property
    def topic_filter(self) -> str:
        return f"{CLOUD_TAG_TOPIC_PREFIX}/#"

    def connect(self) -> None:
        self.client.connect(self.host, self.port, keepalive=30)
        self.client.subscribe(self.topic_filter, qos=0)
        self.client.loop_start()

    def close(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def _on_message(self, _client: Any, _userdata: Any, message: Any) -> None:
        try:
            tag_name, value, timestamp_s = parse_tag_message(message.topic, message.payload)
        except ValueError:
            self.dropped += 1
            return

        self.received += 1
        self.on_tag(tag_name, value, timestamp_s)


def parse_tag_message(topic: str, payload: bytes) -> tuple[str, float, float]:
    prefix = f"{CLOUD_TAG_TOPIC_PREFIX}/"
    if not topic.startswith(prefix):
        raise ValueError(f"unexpected topic: {topic}")

    tag_name = topic.removeprefix(prefix)
    if not tag_name or "/" in tag_name:
        raise ValueError(f"invalid tag topic: {topic}")

    try:
        body = json.loads(payload.decode("utf-8"))
        value = float(body["v"])
        timestamp_s = float(body.get("t", time()))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("payload must be JSON with numeric v and optional numeric t") from exc

    return tag_name, value, timestamp_s
