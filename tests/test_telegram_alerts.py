import json

import pytest

from wtdt.messaging.publisher import build_alarm_payloads
from wtdt.runtime import make_demo_runtime
from wtdt.simulator.process import FaultScenario
from wtdt.telegram_alerts.dashboard import alarm_events_from_snapshot
from wtdt.telegram_alerts.gate import AlarmGate
from wtdt.telegram_alerts.main import format_alarm_message
from wtdt.telegram_alerts.mqtt_source import parse_alarm_event
from wtdt.telegram_alerts.sender import TELEGRAM_MESSAGE_LIMIT, chunks


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_parse_alarm_event_accepts_project_alarm_payload() -> None:
    snapshot = make_demo_runtime(fault=FaultScenario.EQUIPMENT_DOSING_PUMP_FAILURE).tick()
    payload = json.dumps(build_alarm_payloads(snapshot)[0]).encode()

    event = parse_alarm_event(payload)

    assert event.code == "equipment.dosing_pump_failure"
    assert event.severity == "high"
    assert event.evidence
    assert event.recommendation


def test_parse_alarm_event_rejects_missing_code() -> None:
    with pytest.raises(ValueError):
        parse_alarm_event(b'{"severity": "high"}')


def test_alarm_gate_sends_only_fresh_trip_while_alarm_is_active() -> None:
    clock = FakeClock()
    gate = AlarmGate(throttle_s=60.0, clear_after_s=5.0, clock=clock)

    assert gate.observe("equipment.dosing_pump_failure") is True
    clock.advance(1.0)
    assert gate.observe("equipment.dosing_pump_failure") is False
    clock.advance(1.0)
    assert gate.observe("equipment.dosing_pump_failure") is False


def test_alarm_gate_rearms_after_clear_and_throttle_window() -> None:
    clock = FakeClock()
    gate = AlarmGate(throttle_s=10.0, clear_after_s=5.0, clock=clock)

    assert gate.observe("process.ph_excursion") is True
    clock.advance(6.0)
    gate.expire()
    assert gate.observe("process.ph_excursion") is False
    clock.advance(6.0)
    gate.expire()
    assert gate.observe("process.ph_excursion") is True


def test_alarm_message_includes_operator_context() -> None:
    snapshot = make_demo_runtime(fault=FaultScenario.EQUIPMENT_DOSING_PUMP_FAILURE).tick()
    event = parse_alarm_event(json.dumps(build_alarm_payloads(snapshot)[0]).encode())

    message = format_alarm_message(event)

    assert "[ALARM] equipment.dosing_pump_failure" in message
    assert "severity: high" in message
    assert "evidence:" in message
    assert "recommendation:" in message


def test_dashboard_alarm_events_mirror_snapshot_detections() -> None:
    snapshot = make_demo_runtime(fault=FaultScenario.INFRASTRUCTURE_MQTT_DISCONNECTED).tick()

    events = alarm_events_from_snapshot(snapshot)

    assert events
    assert events[0].code == "infrastructure.mqtt_disconnected"
    assert events[0].timestamp_utc == snapshot.timestamp_utc
    assert events[0].sequence == snapshot.sequence


def test_chunks_respect_telegram_limit() -> None:
    parts = chunks("x" * (TELEGRAM_MESSAGE_LIMIT + 5))

    assert len(parts) == 2
    assert len(parts[0]) == TELEGRAM_MESSAGE_LIMIT
    assert len(parts[1]) == 5
