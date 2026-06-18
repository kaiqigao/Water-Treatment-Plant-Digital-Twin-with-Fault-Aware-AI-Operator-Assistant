import json
from dataclasses import dataclass
from typing import Any

from wtdt.messaging.topics import ALARM_EVENT_TOPIC, PLANT_STATE_TOPIC, PLC_COMMAND_TOPIC
from wtdt.runtime import SimulationSnapshot


@dataclass(frozen=True)
class MqttPublishResult:
    topic: str
    payload: str


class MqttTelemetryPublisher:
    def __init__(self, host: str = "localhost", port: int = 1883, client_id: str = "wtdt-sim") -> None:
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError("paho-mqtt is required for MQTT publishing") from exc

        self.host = host
        self.port = port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self.connected = False

    def connect(self) -> None:
        self.client.connect(self.host, self.port, keepalive=30)
        self.client.loop_start()
        self.connected = True

    def close(self) -> None:
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

    def publish_json(self, topic: str, payload: dict[str, Any]) -> MqttPublishResult:
        serialized = json.dumps(payload, sort_keys=True)
        if not self.connected:
            raise RuntimeError("MQTT publisher is not connected")
        self.client.publish(topic, serialized, qos=0, retain=False)
        return MqttPublishResult(topic=topic, payload=serialized)

    def publish_snapshot(self, snapshot: SimulationSnapshot) -> list[MqttPublishResult]:
        results = [
            self.publish_json(PLANT_STATE_TOPIC, build_plant_state_payload(snapshot)),
            self.publish_json(PLC_COMMAND_TOPIC, build_plc_command_payload(snapshot)),
        ]
        for alarm in build_alarm_payloads(snapshot):
            results.append(self.publish_json(ALARM_EVENT_TOPIC, alarm))
        return results


def build_plant_state_payload(snapshot: SimulationSnapshot) -> dict[str, Any]:
    tag_names = [
        "tank_level_pct",
        "reactor_ph",
        "influent_flow_lpm",
        "effluent_flow_lpm",
        "dosing_flow_lpm",
        "active_fault",
        "mqtt_connected",
    ]
    return {
        "timestamp_utc": snapshot.timestamp_utc,
        "sequence": snapshot.sequence,
        "tags": {name: snapshot.tags.get(name) for name in tag_names},
    }


def build_plc_command_payload(snapshot: SimulationSnapshot) -> dict[str, Any]:
    tag_names = [
        "plc_state",
        "ph_setpoint",
        "tank_level_setpoint_pct",
        "inlet_pump_cmd",
        "dosing_pump_cmd_pct",
        "outlet_valve_cmd_pct",
        "level_pid_output_pct",
        "ph_pid_output_pct",
        "level_error_pct",
        "ph_error",
        "alarm_active",
        "fault_code",
    ]
    return {
        "timestamp_utc": snapshot.timestamp_utc,
        "sequence": snapshot.sequence,
        "commands": {name: snapshot.tags.get(name) for name in tag_names},
    }


def build_alarm_payloads(snapshot: SimulationSnapshot) -> list[dict[str, Any]]:
    return [
        {
            "timestamp_utc": snapshot.timestamp_utc,
            "sequence": snapshot.sequence,
            "code": detection.code,
            "severity": detection.severity,
            "evidence": detection.evidence,
            "recommendation": recommendation,
        }
        for detection, recommendation in zip(
            snapshot.detections,
            snapshot.recommendations,
            strict=True,
        )
    ]
