import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from wtdt.messaging.topics import ALARM_EVENT_TOPIC


@dataclass(frozen=True)
class AlarmEvent:
    code: str
    severity: str
    evidence: list[str]
    recommendation: str
    timestamp_utc: str = ""
    sequence: int | None = None


AlarmHandler = Callable[[AlarmEvent], None]


@dataclass
class MqttAlarmSubscriber:
    host: str
    port: int
    on_alarm: AlarmHandler
    topic: str = ALARM_EVENT_TOPIC
    client_id: str = "wtdt-telegram-alerts"

    def __post_init__(self) -> None:
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError("paho-mqtt is required for Telegram alerts") from exc

        self._mqtt = mqtt
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id)
        self.client.on_message = self._on_message
        self.received = 0
        self.dropped = 0

    def connect(self) -> None:
        self.client.connect(self.host, self.port, keepalive=30)
        self.client.subscribe(self.topic, qos=0)
        self.client.loop_start()

    def close(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def _on_message(self, _client: Any, _userdata: Any, message: Any) -> None:
        try:
            event = parse_alarm_event(message.payload)
        except ValueError:
            self.dropped += 1
            return

        self.received += 1
        self.on_alarm(event)


def parse_alarm_event(payload: bytes) -> AlarmEvent:
    try:
        body = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("alarm event payload must be UTF-8 JSON") from exc

    code = _required_text(body, "code")
    severity = _optional_text(body, "severity", "unknown")
    recommendation = _optional_text(body, "recommendation", "")
    timestamp_utc = _optional_text(body, "timestamp_utc", "")
    sequence = body.get("sequence")
    evidence = _evidence_list(body.get("evidence", []))

    if sequence is not None:
        try:
            sequence = int(sequence)
        except (TypeError, ValueError) as exc:
            raise ValueError("alarm event sequence must be an integer") from exc

    return AlarmEvent(
        code=code,
        severity=severity,
        evidence=evidence,
        recommendation=recommendation,
        timestamp_utc=timestamp_utc,
        sequence=sequence,
    )


def _required_text(body: dict[str, Any], key: str) -> str:
    value = _optional_text(body, key, "")
    if not value:
        raise ValueError(f"alarm event requires non-empty {key}")
    return value


def _optional_text(body: dict[str, Any], key: str, default: str) -> str:
    value = body.get(key, default)
    if value is None:
        return default
    return str(value).strip()


def _evidence_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []

