from wtdt.messaging.publisher import (
    build_alarm_payloads,
    build_cloud_tag_payloads,
    build_plant_state_payload,
    build_plc_command_payload,
)
from wtdt.messaging.topics import cloud_tag_topic, topic_for
from wtdt.runtime import make_demo_runtime
from wtdt.simulator.process import FaultScenario


def test_topics_cover_required_message_groups() -> None:
    assert topic_for("plant_state").endswith("/plant/state")
    assert topic_for("plc_command").endswith("/plc/command")
    assert topic_for("alarm_event").endswith("/alarm/event")
    assert topic_for("fault_injection").endswith("/fault/injection")
    assert cloud_tag_topic("LT_101") == "plant/tags/LT_101"


def test_snapshot_builds_mqtt_payloads() -> None:
    snapshot = make_demo_runtime(fault=FaultScenario.EQUIPMENT_DOSING_PUMP_FAILURE).tick()

    plant_payload = build_plant_state_payload(snapshot)
    command_payload = build_plc_command_payload(snapshot)
    alarm_payloads = build_alarm_payloads(snapshot)

    assert plant_payload["tags"]["tank_level_pct"] == snapshot.tags["tank_level_pct"]
    assert command_payload["commands"]["plc_state"] == snapshot.tags["plc_state"]
    assert alarm_payloads[0]["code"] == "equipment.dosing_pump_failure"


def test_snapshot_builds_cloud_bridge_tag_payloads() -> None:
    snapshot = make_demo_runtime().tick()

    cloud_payloads = dict(build_cloud_tag_payloads(snapshot))

    assert cloud_payloads["plant/tags/tank_level_pct"]["v"] == snapshot.tags["tank_level_pct"]
    assert cloud_payloads["plant/tags/inlet_pump_cmd"]["v"] in {0.0, 1.0}
    assert cloud_payloads["plant/tags/ALARM_ACTIVE"]["v"] == 0.0
    assert all("active_fault" not in topic for topic in cloud_payloads)
