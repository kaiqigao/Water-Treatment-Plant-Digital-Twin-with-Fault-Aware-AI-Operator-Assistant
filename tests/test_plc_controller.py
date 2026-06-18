from wtdt.plc.controller import PlcState, SimulatedPlc
from wtdt.simulator.process import PlantState, WaterTreatmentProcess


def test_low_level_starts_filling() -> None:
    plc = SimulatedPlc()

    commands = plc.scan(tank_level_pct=35.0, reactor_ph=7.0)

    assert commands["plc_state"] == PlcState.FILLING.value
    assert commands["inlet_pump_cmd"] is True
    assert commands["outlet_valve_cmd_pct"] == 0.0
    assert commands["alarm_active"] is False


def test_high_level_enters_discharge_without_fault() -> None:
    plc = SimulatedPlc()

    commands = plc.scan(tank_level_pct=90.0, reactor_ph=7.0)

    assert commands["plc_state"] == PlcState.DISCHARGING.value
    assert commands["inlet_pump_cmd"] is False
    assert commands["outlet_valve_cmd_pct"] == 80.0
    assert commands["alarm_active"] is False


def test_level_hysteresis_keeps_filling_until_stop_threshold() -> None:
    plc = SimulatedPlc()

    plc.scan(tank_level_pct=39.0, reactor_ph=7.0)
    commands = plc.scan(tank_level_pct=50.0, reactor_ph=7.0)

    assert commands["plc_state"] == PlcState.FILLING.value

    commands = plc.scan(tank_level_pct=56.0, reactor_ph=7.0)

    assert commands["plc_state"] == PlcState.TREATING.value


def test_low_ph_increases_dosing_command() -> None:
    plc = SimulatedPlc()

    commands = plc.scan(tank_level_pct=60.0, reactor_ph=6.6)

    assert commands["plc_state"] == PlcState.TREATING.value
    assert commands["dosing_pump_cmd_pct"] > 0.0
    assert commands["ph_setpoint"] == 7.0


def test_high_ph_stops_dosing_without_fault_inside_safe_range() -> None:
    plc = SimulatedPlc()

    commands = plc.scan(tank_level_pct=60.0, reactor_ph=7.8)

    assert commands["plc_state"] == PlcState.TREATING.value
    assert commands["dosing_pump_cmd_pct"] == 0.0
    assert commands["alarm_active"] is False


def test_unsafe_ph_enters_latched_fault_until_reset() -> None:
    plc = SimulatedPlc()

    fault_commands = plc.scan(tank_level_pct=60.0, reactor_ph=5.4)

    assert fault_commands["plc_state"] == PlcState.FAULT.value
    assert fault_commands["inlet_pump_cmd"] is False
    assert fault_commands["dosing_pump_cmd_pct"] == 0.0
    assert fault_commands["alarm_active"] is True
    assert fault_commands["fault_code"] == "process.ph_unsafe"

    latched_commands = plc.scan(tank_level_pct=60.0, reactor_ph=7.0)

    assert latched_commands["plc_state"] == PlcState.FAULT.value
    assert latched_commands["fault_code"] == "plc.latched_fault"

    plc.reset()
    reset_commands = plc.scan(tank_level_pct=60.0, reactor_ph=7.0)

    assert reset_commands["plc_state"] == PlcState.TREATING.value


def test_plc_commands_feed_the_process_simulator() -> None:
    plc = SimulatedPlc()
    process = WaterTreatmentProcess(PlantState(tank_level_pct=35.0, reactor_ph=6.6))

    commands = plc.scan(
        tank_level_pct=process.state.tank_level_pct,
        reactor_ph=process.state.reactor_ph,
    )
    state = process.apply_controls(
        inlet_pump_cmd=bool(commands["inlet_pump_cmd"]),
        outlet_valve_cmd_pct=float(commands["outlet_valve_cmd_pct"]),
        dosing_pump_cmd_pct=float(commands["dosing_pump_cmd_pct"]),
    )

    assert state.influent_flow_lpm > 0.0
    assert state.dosing_flow_lpm > 0.0
