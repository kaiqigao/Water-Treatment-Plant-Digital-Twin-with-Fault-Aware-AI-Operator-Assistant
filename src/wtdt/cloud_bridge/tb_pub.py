import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ThingsBoardPublisher:
    token: str
    host: str = "mqtt.thingsboard.cloud"
    port: int = 1883
    client_id: str = "wtdt-cloud-bridge"

    def __post_init__(self) -> None:
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError("paho-mqtt is required for the cloud bridge") from exc

        self._mqtt = mqtt
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id)

    def connect(self) -> None:
        if not self.token or self.token == "paste_your_device_access_token_here":
            raise RuntimeError("TB_TOKEN must be set to a ThingsBoard device access token")
        self.client.username_pw_set(self.token)
        self.client.connect(self.host, self.port, keepalive=30)
        self.client.loop_start()

    def publish(self, payload: dict[str, Any]) -> None:
        serialized = json.dumps(payload, sort_keys=True)
        self.client.publish("v1/devices/me/telemetry", serialized, qos=0, retain=False)

    def close(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
