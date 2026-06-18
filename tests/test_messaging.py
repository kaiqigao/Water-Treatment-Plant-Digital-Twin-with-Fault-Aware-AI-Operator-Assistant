from wtdt.messaging.publisher import (
    build_alarm_payloads,
    build_plant_state_payload,
    build_plc_command_payload,
)
from wtdt.messaging.topics import topic_for
from wtdt.runtime import make_demo_runtime
from wtdt.simulator.process import FaultScenario


def test_topics_cover_required_message_groups() -> None:
    assert topic_for("plant_state").endswith("/plant/state")
    assert topic_for("plc_command").endswith("/plc/command")
    assert topic_for("alarm_event").endswith("/alarm/event")
    assert topic_for("fault_injection").endswith("/fault/injection")


def test_snapshot_builds_mqtt_payloads() -> None:
    snapshot = make_demo_runtime(fault=FaultScenario.EQUIPMENT_DOSING_PUMP_FAILURE).tick()

    plant_payload = build_plant_state_payload(snapshot)
    command_payload = build_plc_command_payload(snapshot)
    alarm_payloads = build_alarm_payloads(snapshot)

    assert plant_payload["tags"]["tank_level_pct"] == snapshot.tags["tank_level_pct"]
    assert command_payload["commands"]["plc_state"] == snapshot.tags["plc_state"]
    assert alarm_payloads[0]["code"] == "equipment.dosing_pump_failure"
