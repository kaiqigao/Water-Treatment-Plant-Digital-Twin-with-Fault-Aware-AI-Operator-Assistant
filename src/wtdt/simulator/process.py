from dataclasses import dataclass
from enum import StrEnum


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


@dataclass
class PlantState:
    tank_level_pct: float = 50.0
    reactor_ph: float = 7.0
    influent_flow_lpm: float = 20.0
    effluent_flow_lpm: float = 20.0
    dosing_flow_lpm: float = 0.0

    def as_tags(self) -> dict[str, float]:
        return {
            "tank_level_pct": self.tank_level_pct,
            "reactor_ph": self.reactor_ph,
            "influent_flow_lpm": self.influent_flow_lpm,
            "effluent_flow_lpm": self.effluent_flow_lpm,
            "dosing_flow_lpm": self.dosing_flow_lpm,
        }


class FaultScenario(StrEnum):
    SENSOR_PH_DRIFT = "sensor.ph_drift"
    SENSOR_PH_STUCK = "sensor.ph_stuck"
    EQUIPMENT_DOSING_PUMP_FAILURE = "equipment.dosing_pump_failure"
    EQUIPMENT_OUTLET_VALVE_STUCK = "equipment.outlet_valve_stuck"
    PROCESS_PH_SHOCK = "process.ph_shock"
    PROCESS_INFLUENT_SURGE = "process.influent_surge"
    INFRASTRUCTURE_MQTT_DISCONNECTED = "infrastructure.mqtt_disconnected"


@dataclass(frozen=True)
class ProcessConfig:
    tank_volume_l: float = 1_000.0
    max_influent_flow_lpm: float = 80.0
    max_effluent_flow_lpm: float = 80.0
    max_dosing_flow_lpm: float = 5.0
    influent_ph: float = 7.0
    dosing_ph_gain_per_l: float = 0.25
    ph_mixing_time_s: float = 180.0


class WaterTreatmentProcess:
    """Deterministic water treatment process model for the plant digital twin."""

    def __init__(self, state: PlantState | None = None, config: ProcessConfig | None = None) -> None:
        self.config = config or ProcessConfig()
        self.state = state or PlantState()
        self.elapsed_seconds = 0.0
        self.active_fault: FaultScenario | None = None
        self._stuck_reactor_ph: float | None = None
        self._limit_state()

    def inject_fault(self, scenario: FaultScenario | str) -> None:
        self.active_fault = FaultScenario(scenario)
        if self.active_fault == FaultScenario.SENSOR_PH_STUCK:
            self._stuck_reactor_ph = self.state.reactor_ph
        elif self.active_fault == FaultScenario.EQUIPMENT_DOSING_PUMP_FAILURE:
            self.state.reactor_ph = min(self.state.reactor_ph, 6.6)
        elif self.active_fault == FaultScenario.EQUIPMENT_OUTLET_VALVE_STUCK:
            self.state.tank_level_pct = max(self.state.tank_level_pct, 86.0)

    def clear_fault(self) -> None:
        self.active_fault = None
        self._stuck_reactor_ph = None

    def apply_controls(
        self,
        *,
        inlet_pump_cmd: bool,
        outlet_valve_cmd_pct: float,
        dosing_pump_cmd_pct: float,
    ) -> PlantState:
        """Convert PLC-style actuator commands into process flows."""
        outlet_pct = _clamp(outlet_valve_cmd_pct, 0.0, 100.0)
        dosing_pct = _clamp(dosing_pump_cmd_pct, 0.0, 100.0)

        influent_flow_lpm = self.config.max_influent_flow_lpm if inlet_pump_cmd else 0.0
        if self.active_fault == FaultScenario.PROCESS_INFLUENT_SURGE:
            influent_flow_lpm = max(influent_flow_lpm, self.config.max_influent_flow_lpm * 0.75)

        effluent_flow_lpm = self.config.max_effluent_flow_lpm * outlet_pct / 100.0
        if self.active_fault == FaultScenario.EQUIPMENT_OUTLET_VALVE_STUCK:
            effluent_flow_lpm = 0.0

        dosing_flow_lpm = self.config.max_dosing_flow_lpm * dosing_pct / 100.0
        if self.active_fault == FaultScenario.EQUIPMENT_DOSING_PUMP_FAILURE:
            dosing_flow_lpm = 0.0

        self.state.influent_flow_lpm = influent_flow_lpm
        self.state.effluent_flow_lpm = effluent_flow_lpm
        self.state.dosing_flow_lpm = dosing_flow_lpm
        return self._limit_state()

    def step(self, seconds: float = 1.0) -> PlantState:
        if seconds < 0.0:
            raise ValueError("seconds must be non-negative")

        self._limit_state()
        self.elapsed_seconds += seconds
        balance = self.state.influent_flow_lpm - self.state.effluent_flow_lpm
        level_delta_pct = balance * seconds / 60.0 / self.config.tank_volume_l * 100.0
        self.state.tank_level_pct = _clamp(self.state.tank_level_pct + level_delta_pct, 0.0, 100.0)

        mixing_factor = _clamp(seconds / self.config.ph_mixing_time_s, 0.0, 1.0)
        influent_ph = 5.2 if self.active_fault == FaultScenario.PROCESS_PH_SHOCK else self.config.influent_ph
        neutral_mixing = (influent_ph - self.state.reactor_ph) * mixing_factor
        dosing_effect = self.state.dosing_flow_lpm * self.config.dosing_ph_gain_per_l * seconds / 60.0
        self.state.reactor_ph = _clamp(
            self.state.reactor_ph + neutral_mixing + dosing_effect,
            0.0,
            14.0,
        )
        return self._limit_state()

    def read_tags(self) -> dict[str, float | bool | str]:
        measured_level = self.state.tank_level_pct
        measured_ph = self.state.reactor_ph

        if self.active_fault == FaultScenario.SENSOR_PH_DRIFT:
            measured_ph = _clamp(self.state.reactor_ph + 0.9, 0.0, 14.0)
        elif self.active_fault == FaultScenario.SENSOR_PH_STUCK:
            if self._stuck_reactor_ph is None:
                self._stuck_reactor_ph = self.state.reactor_ph
            measured_ph = self._stuck_reactor_ph

        tags: dict[str, float | bool | str] = {
            "tank_level_pct": measured_level,
            "reactor_ph": measured_ph,
            "actual_tank_level_pct": self.state.tank_level_pct,
            "actual_reactor_ph": self.state.reactor_ph,
            "influent_flow_lpm": self.state.influent_flow_lpm,
            "effluent_flow_lpm": self.state.effluent_flow_lpm,
            "dosing_flow_lpm": self.state.dosing_flow_lpm,
            "active_fault": self.active_fault.value if self.active_fault else "",
            "mqtt_connected": self.active_fault != FaultScenario.INFRASTRUCTURE_MQTT_DISCONNECTED,
            "elapsed_seconds": self.elapsed_seconds,
        }
        return tags

    def _limit_state(self) -> PlantState:
        self.state.tank_level_pct = _clamp(self.state.tank_level_pct, 0.0, 100.0)
        self.state.reactor_ph = _clamp(self.state.reactor_ph, 0.0, 14.0)
        self.state.influent_flow_lpm = _clamp(
            self.state.influent_flow_lpm,
            0.0,
            self.config.max_influent_flow_lpm,
        )
        self.state.effluent_flow_lpm = _clamp(
            self.state.effluent_flow_lpm,
            0.0,
            self.config.max_effluent_flow_lpm,
        )
        self.state.dosing_flow_lpm = _clamp(
            self.state.dosing_flow_lpm,
            0.0,
            self.config.max_dosing_flow_lpm,
        )
        return self.state
