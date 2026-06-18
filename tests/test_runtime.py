from wtdt.runtime import format_snapshot, make_demo_runtime
from wtdt.simulator.process import FaultScenario, PlantState


def test_runtime_tick_closes_plc_process_detection_loop() -> None:
    runtime = make_demo_runtime(initial_state=PlantState(tank_level_pct=35.0, reactor_ph=6.6))

    snapshot = runtime.tick()

    assert snapshot.tags["plc_state"] == "filling"
    assert snapshot.tags["inlet_pump_cmd"] is True
    assert snapshot.tags["dosing_flow_lpm"] > 0.0
    assert "level=" in format_snapshot(snapshot)


def test_runtime_fault_injection_surfaces_alarm_and_recommendation() -> None:
    runtime = make_demo_runtime(fault=FaultScenario.EQUIPMENT_DOSING_PUMP_FAILURE)

    snapshot = runtime.tick()

    assert any(detection.code == "equipment.dosing_pump_failure" for detection in snapshot.detections)
    assert snapshot.recommendations
    assert snapshot.alarm_active is True


def test_runtime_process_faults_alarm_on_first_tick() -> None:
    for scenario in [FaultScenario.PROCESS_PH_SHOCK, FaultScenario.PROCESS_INFLUENT_SURGE]:
        snapshot = make_demo_runtime(fault=scenario).tick()

        assert any(detection.code == scenario.value for detection in snapshot.detections)
        assert snapshot.alarm_active is True


def test_runtime_infrastructure_fault_alarms_on_first_tick() -> None:
    snapshot = make_demo_runtime(fault=FaultScenario.INFRASTRUCTURE_MQTT_DISCONNECTED).tick()

    assert any(
        detection.code == "infrastructure.mqtt_disconnected"
        for detection in snapshot.detections
    )
    assert snapshot.alarm_active is True


def test_runtime_applies_operator_setpoints_to_pid_tags() -> None:
    runtime = make_demo_runtime(initial_state=PlantState(tank_level_pct=45.0, reactor_ph=7.0))

    runtime.set_setpoints(ph_setpoint=7.4, tank_level_setpoint_pct=70.0)
    snapshot = runtime.tick(seconds=5.0)

    assert snapshot.tags["ph_setpoint"] == 7.4
    assert snapshot.tags["tank_level_setpoint_pct"] == 70.0
    assert snapshot.tags["ph_pid_output_pct"] > 0.0
    assert snapshot.tags["level_pid_output_pct"] > 0.0
    assert snapshot.tags["simulation_seconds_per_tick"] == 5.0
