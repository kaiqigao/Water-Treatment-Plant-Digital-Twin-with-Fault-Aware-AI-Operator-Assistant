from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class PlcState(StrEnum):
    STOPPED = "stopped"
    FILLING = "filling"
    TREATING = "treating"
    DISCHARGING = "discharging"
    FAULT = "fault"


@dataclass(frozen=True)
class PlcConfig:
    fill_start_pct: float = 40.0
    fill_stop_pct: float = 55.0
    discharge_start_pct: float = 85.0
    discharge_stop_pct: float = 70.0
    critical_low_level_pct: float = 5.0
    critical_high_level_pct: float = 98.0
    ph_setpoint: float = 7.0
    dosing_start_ph: float = 6.9
    unsafe_low_ph: float = 5.5
    unsafe_high_ph: float = 8.8
    treating_outlet_valve_cmd_pct: float = 45.0
    discharge_outlet_valve_cmd_pct: float = 80.0
    minimum_dosing_cmd_pct: float = 25.0
    dosing_gain_pct_per_ph: float = 40.0


class SimulatedPlc:
    """Deterministic PLC state machine for the water treatment simulator."""

    def __init__(self, config: PlcConfig | None = None) -> None:
        self.config = config or PlcConfig()
        self.state = PlcState.STOPPED

    def scan(self, tank_level_pct: float, reactor_ph: float) -> dict[str, float | str | bool]:
        fault_code = self._detect_fault(tank_level_pct, reactor_ph)
        if fault_code or self.state == PlcState.FAULT:
            self.state = PlcState.FAULT
            return self._commands(tank_level_pct, reactor_ph, fault_code or "plc.latched_fault")

        self.state = self._next_state(tank_level_pct)
        return self._commands(tank_level_pct, reactor_ph)

    def reset(self) -> None:
        """Clear a latched fault after the operator has verified safe conditions."""
        self.state = PlcState.STOPPED

    def _next_state(self, tank_level_pct: float) -> PlcState:
        if (
            tank_level_pct >= self.config.discharge_start_pct
            or self.state == PlcState.DISCHARGING
            and tank_level_pct > self.config.discharge_stop_pct
        ):
            return PlcState.DISCHARGING

        if (
            tank_level_pct <= self.config.fill_start_pct
            or self.state == PlcState.FILLING
            and tank_level_pct < self.config.fill_stop_pct
        ):
            return PlcState.FILLING

        return PlcState.TREATING

    def _detect_fault(self, tank_level_pct: float, reactor_ph: float) -> str:
        if not isfinite(tank_level_pct) or not isfinite(reactor_ph):
            return "sensor.invalid_reading"
        if tank_level_pct < 0.0 or tank_level_pct > 100.0 or reactor_ph < 0.0 or reactor_ph > 14.0:
            return "sensor.out_of_range"
        if tank_level_pct <= self.config.critical_low_level_pct:
            return "process.tank_critically_low"
        if tank_level_pct >= self.config.critical_high_level_pct:
            return "process.tank_critically_high"
        if reactor_ph <= self.config.unsafe_low_ph or reactor_ph >= self.config.unsafe_high_ph:
            return "process.ph_unsafe"
        return ""

    def _commands(
        self,
        tank_level_pct: float,
        reactor_ph: float,
        fault_code: str = "",
    ) -> dict[str, float | str | bool]:
        if self.state == PlcState.FAULT:
            return {
                "plc_state": self.state.value,
                "ph_setpoint": self.config.ph_setpoint,
                "inlet_pump_cmd": False,
                "dosing_pump_cmd_pct": 0.0,
                "outlet_valve_cmd_pct": 100.0
                if tank_level_pct >= self.config.critical_high_level_pct
                else 0.0,
                "alarm_active": True,
                "fault_code": fault_code,
            }

        inlet_pump_cmd = self.state == PlcState.FILLING
        outlet_valve_cmd_pct = 0.0
        if self.state == PlcState.TREATING:
            outlet_valve_cmd_pct = self.config.treating_outlet_valve_cmd_pct
        elif self.state == PlcState.DISCHARGING:
            outlet_valve_cmd_pct = self.config.discharge_outlet_valve_cmd_pct

        return {
            "plc_state": self.state.value,
            "ph_setpoint": self.config.ph_setpoint,
            "inlet_pump_cmd": inlet_pump_cmd,
            "dosing_pump_cmd_pct": self._dosing_command_pct(reactor_ph),
            "outlet_valve_cmd_pct": outlet_valve_cmd_pct,
            "alarm_active": False,
            "fault_code": "",
        }

    def _dosing_command_pct(self, reactor_ph: float) -> float:
        if reactor_ph >= self.config.dosing_start_ph:
            return 0.0

        correction = (self.config.dosing_start_ph - reactor_ph) * self.config.dosing_gain_pct_per_ph
        return min(100.0, self.config.minimum_dosing_cmd_pct + correction)
