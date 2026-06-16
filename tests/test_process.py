import pytest

from wtdt.simulator.process import PlantState, WaterTreatmentProcess


def test_tank_level_rises_when_influent_exceeds_effluent() -> None:
    process = WaterTreatmentProcess(
        PlantState(influent_flow_lpm=30.0, effluent_flow_lpm=20.0),
    )

    state = process.step(seconds=60.0)

    assert state.tank_level_pct == pytest.approx(51.0)


def test_tank_level_falls_when_effluent_exceeds_influent() -> None:
    process = WaterTreatmentProcess(
        PlantState(influent_flow_lpm=10.0, effluent_flow_lpm=20.0),
    )

    state = process.step(seconds=60.0)

    assert state.tank_level_pct == pytest.approx(49.0)


def test_dosing_flow_gradually_increases_reactor_ph() -> None:
    process = WaterTreatmentProcess(
        PlantState(reactor_ph=6.8, dosing_flow_lpm=2.0),
    )

    state = process.step(seconds=60.0)

    assert state.reactor_ph > 6.8


def test_state_values_are_limited_to_reasonable_ranges() -> None:
    process = WaterTreatmentProcess(
        PlantState(
            tank_level_pct=99.0,
            reactor_ph=13.9,
            influent_flow_lpm=200.0,
            effluent_flow_lpm=-10.0,
            dosing_flow_lpm=20.0,
        ),
    )

    state = process.step(seconds=60.0)

    assert 0.0 <= state.tank_level_pct <= 100.0
    assert 0.0 <= state.reactor_ph <= 14.0
    assert 0.0 <= state.influent_flow_lpm <= process.config.max_influent_flow_lpm
    assert 0.0 <= state.effluent_flow_lpm <= process.config.max_effluent_flow_lpm
    assert 0.0 <= state.dosing_flow_lpm <= process.config.max_dosing_flow_lpm


def test_apply_controls_maps_plc_commands_to_process_flows() -> None:
    process = WaterTreatmentProcess()

    state = process.apply_controls(
        inlet_pump_cmd=True,
        outlet_valve_cmd_pct=50.0,
        dosing_pump_cmd_pct=20.0,
    )

    assert state.influent_flow_lpm == pytest.approx(80.0)
    assert state.effluent_flow_lpm == pytest.approx(40.0)
    assert state.dosing_flow_lpm == pytest.approx(1.0)


def test_plant_state_exports_standard_process_tags() -> None:
    state = PlantState(
        tank_level_pct=42.0,
        reactor_ph=6.9,
        influent_flow_lpm=30.0,
        effluent_flow_lpm=25.0,
        dosing_flow_lpm=0.5,
    )

    assert state.as_tags() == {
        "tank_level_pct": 42.0,
        "reactor_ph": 6.9,
        "influent_flow_lpm": 30.0,
        "effluent_flow_lpm": 25.0,
        "dosing_flow_lpm": 0.5,
    }
