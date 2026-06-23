from wtdt.agent.operator_agent import diagnose_snapshot, diagnose_tags
from wtdt.runtime import make_demo_runtime
from wtdt.simulator.process import FaultScenario


def test_operator_agent_reports_clear_state() -> None:
    snapshot = make_demo_runtime().tick()

    diagnosis = diagnose_snapshot(snapshot)

    assert diagnosis.state == "clear"
    assert diagnosis.severity == "none"
    assert "No operator intervention" in diagnosis.actions[0]


def test_operator_agent_explains_active_fault_with_checks() -> None:
    snapshot = make_demo_runtime(fault=FaultScenario.EQUIPMENT_DOSING_PUMP_FAILURE).tick()

    diagnosis = diagnose_snapshot(snapshot)

    assert diagnosis.state == "alarm"
    assert diagnosis.severity == "high"
    assert any("dosing pump" in item.lower() for item in diagnosis.likely_causes)
    assert any("pump power" in item.lower() for item in diagnosis.checks)
    assert diagnosis.actions


def test_operator_agent_can_diagnose_plain_tags_for_external_callers() -> None:
    diagnosis = diagnose_tags({"mqtt_connected": False, "tank_level_pct": 50.0, "reactor_ph": 7.0})

    assert diagnosis.state == "alarm"
    assert any("MQTT" in item for item in diagnosis.likely_causes)
