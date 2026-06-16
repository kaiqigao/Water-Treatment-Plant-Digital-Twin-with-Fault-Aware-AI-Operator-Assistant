from enum import StrEnum


class PlcState(StrEnum):
    STOPPED = "stopped"
    FILLING = "filling"
    TREATING = "treating"
    DISCHARGING = "discharging"
    FAULT = "fault"


class SimulatedPlc:
    """Placeholder PLC controller with a deterministic scan method."""

    def __init__(self) -> None:
        self.state = PlcState.STOPPED

    def scan(self, tank_level_pct: float, reactor_ph: float) -> dict[str, float | str | bool]:
        if tank_level_pct >= 95.0 or reactor_ph < 5.5 or reactor_ph > 8.5:
            self.state = PlcState.FAULT
        elif tank_level_pct < 40.0:
            self.state = PlcState.FILLING
        else:
            self.state = PlcState.TREATING

        return {
            "plc_state": self.state.value,
            "inlet_pump_cmd": self.state == PlcState.FILLING,
            "dosing_pump_cmd_pct": 50.0 if reactor_ph < 6.9 else 0.0,
            "outlet_valve_cmd_pct": 50.0 if self.state == PlcState.TREATING else 0.0,
        }
