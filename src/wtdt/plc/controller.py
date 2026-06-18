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
    tank_level_setpoint_pct: float = 55.0
    level_pid_kp: float = 7.0
    level_pid_ki: float = 0.08
    level_pid_kd: float = 0.0
    ph_pid_kp: float = 75.0
    ph_pid_ki: float = 1.2
    ph_pid_kd: float = 0.0


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


class SimulatedPlc:
    """Deterministic PLC state machine for the water treatment simulator."""

    def __init__(self, config: PlcConfig | None = None) -> None:
        self.config = config or PlcConfig()
        self.state = PlcState.STOPPED
        self.ph_setpoint = self.config.ph_setpoint
        self.tank_level_setpoint_pct = self.config.tank_level_setpoint_pct
        self._level_integral = 0.0
        self._level_previous_error = 0.0
        self._ph_integral = 0.0
        self._ph_previous_error = 0.0

    def scan(
        self,
        tank_level_pct: float,
        reactor_ph: float,
        *,
        ph_setpoint: float | None = None,
        tank_level_setpoint_pct: float | None = None,
        seconds: float = 1.0,
    ) -> dict[str, float | str | bool]:
        self.ph_setpoint = _clamp(ph_setpoint or self.ph_setpoint, 6.5, 8.2)
        self.tank_level_setpoint_pct = _clamp(
            tank_level_setpoint_pct or self.tank_level_setpoint_pct,
            25.0,
            85.0,
        )
        fault_code = self._detect_fault(tank_level_pct, reactor_ph)
        if fault_code or self.state == PlcState.FAULT:
            self.state = PlcState.FAULT
            return self._commands(tank_level_pct, reactor_ph, fault_code or "plc.latched_fault")

        self.state = self._next_state(tank_level_pct)
        return self._commands(tank_level_pct, reactor_ph, seconds=seconds)

    def reset(self) -> None:
        """Clear a latched fault after the operator has verified safe conditions."""
        self.state = PlcState.STOPPED
        self._level_integral = 0.0
        self._level_previous_error = 0.0
        self._ph_integral = 0.0
        self._ph_previous_error = 0.0

    def _next_state(self, tank_level_pct: float) -> PlcState:
        if (
            tank_level_pct >= self.config.discharge_start_pct
            or self.state == PlcState.DISCHARGING
            and tank_level_pct > self.config.discharge_stop_pct
        ):
            return PlcState.DISCHARGING

        if (
            tank_level_pct <= self.tank_level_setpoint_pct - 2.0
            or self.state == PlcState.FILLING
            and tank_level_pct < self.tank_level_setpoint_pct - 0.5
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
        seconds: float = 1.0,
    ) -> dict[str, float | str | bool]:
        if self.state == PlcState.FAULT:
            return {
                "plc_state": self.state.value,
                "ph_setpoint": self.ph_setpoint,
                "tank_level_setpoint_pct": self.tank_level_setpoint_pct,
                "inlet_pump_cmd": False,
                "dosing_pump_cmd_pct": 0.0,
                "outlet_valve_cmd_pct": 100.0
                if tank_level_pct >= self.config.critical_high_level_pct
                else 0.0,
                "level_pid_output_pct": 0.0,
                "ph_pid_output_pct": 0.0,
                "level_error_pct": self.tank_level_setpoint_pct - tank_level_pct,
                "ph_error": self.ph_setpoint - reactor_ph,
                "alarm_active": True,
                "fault_code": fault_code,
            }

        level_pid_output_pct = self._level_pid_output(tank_level_pct, seconds)
        inlet_pump_cmd = level_pid_output_pct > 5.0 or self.state == PlcState.FILLING
        outlet_valve_cmd_pct = 0.0 if inlet_pump_cmd else min(100.0, max(0.0, -level_pid_output_pct))
        if self.state == PlcState.DISCHARGING:
            inlet_pump_cmd = False
            outlet_valve_cmd_pct = self.config.discharge_outlet_valve_cmd_pct

        ph_pid_output_pct = self._ph_pid_output(reactor_ph, seconds)

        return {
            "plc_state": self.state.value,
            "ph_setpoint": self.ph_setpoint,
            "tank_level_setpoint_pct": self.tank_level_setpoint_pct,
            "inlet_pump_cmd": inlet_pump_cmd,
            "dosing_pump_cmd_pct": ph_pid_output_pct,
            "outlet_valve_cmd_pct": outlet_valve_cmd_pct,
            "level_pid_output_pct": level_pid_output_pct,
            "ph_pid_output_pct": ph_pid_output_pct,
            "level_error_pct": self.tank_level_setpoint_pct - tank_level_pct,
            "ph_error": self.ph_setpoint - reactor_ph,
            "alarm_active": False,
            "fault_code": "",
        }

    def _level_pid_output(self, tank_level_pct: float, seconds: float) -> float:
        error = self.tank_level_setpoint_pct - tank_level_pct
        self._level_integral = _clamp(self._level_integral + error * seconds, -250.0, 250.0)
        derivative = (error - self._level_previous_error) / seconds if seconds > 0.0 else 0.0
        self._level_previous_error = error
        output = (
            self.config.level_pid_kp * error
            + self.config.level_pid_ki * self._level_integral
            + self.config.level_pid_kd * derivative
        )
        return _clamp(output, -100.0, 100.0)

    def _ph_pid_output(self, reactor_ph: float, seconds: float) -> float:
        error = self.ph_setpoint - reactor_ph
        if error <= 0.0:
            self._ph_integral = 0.0
            self._ph_previous_error = error
            return 0.0

        self._ph_integral = _clamp(self._ph_integral + error * seconds, -50.0, 50.0)
        derivative = (error - self._ph_previous_error) / seconds if seconds > 0.0 else 0.0
        self._ph_previous_error = error
        output = (
            self.config.ph_pid_kp * error
            + self.config.ph_pid_ki * self._ph_integral
            + self.config.ph_pid_kd * derivative
        )
        return _clamp(output, 0.0, 100.0)
