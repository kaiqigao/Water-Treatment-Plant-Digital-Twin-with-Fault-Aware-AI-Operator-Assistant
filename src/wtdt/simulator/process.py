from dataclasses import dataclass


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


@dataclass
class PlantState:
    tank_level_pct: float = 50.0
    reactor_ph: float = 7.0
    influent_flow_lpm: float = 20.0
    effluent_flow_lpm: float = 20.0
    dosing_flow_lpm: float = 0.0


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
        self._limit_state()

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

        self.state.influent_flow_lpm = self.config.max_influent_flow_lpm if inlet_pump_cmd else 0.0
        self.state.effluent_flow_lpm = self.config.max_effluent_flow_lpm * outlet_pct / 100.0
        self.state.dosing_flow_lpm = self.config.max_dosing_flow_lpm * dosing_pct / 100.0
        return self._limit_state()

    def step(self, seconds: float = 1.0) -> PlantState:
        if seconds < 0.0:
            raise ValueError("seconds must be non-negative")

        self._limit_state()
        balance = self.state.influent_flow_lpm - self.state.effluent_flow_lpm
        level_delta_pct = balance * seconds / 60.0 / self.config.tank_volume_l * 100.0
        self.state.tank_level_pct = _clamp(self.state.tank_level_pct + level_delta_pct, 0.0, 100.0)

        mixing_factor = _clamp(seconds / self.config.ph_mixing_time_s, 0.0, 1.0)
        neutral_mixing = (self.config.influent_ph - self.state.reactor_ph) * mixing_factor
        dosing_effect = self.state.dosing_flow_lpm * self.config.dosing_ph_gain_per_l * seconds / 60.0
        self.state.reactor_ph = _clamp(
            self.state.reactor_ph + neutral_mixing + dosing_effect,
            0.0,
            14.0,
        )
        return self._limit_state()

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
