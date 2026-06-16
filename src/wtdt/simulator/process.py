from dataclasses import dataclass


@dataclass
class PlantState:
    tank_level_pct: float = 50.0
    reactor_ph: float = 7.0
    influent_flow_lpm: float = 20.0
    effluent_flow_lpm: float = 20.0
    dosing_flow_lpm: float = 0.0


class WaterTreatmentProcess:
    """Minimal process placeholder for the plant digital twin."""

    def __init__(self) -> None:
        self.state = PlantState()

    def step(self, seconds: float = 1.0) -> PlantState:
        balance = self.state.influent_flow_lpm - self.state.effluent_flow_lpm
        self.state.tank_level_pct = max(0.0, min(100.0, self.state.tank_level_pct + balance * 0.01 * seconds))
        return self.state
