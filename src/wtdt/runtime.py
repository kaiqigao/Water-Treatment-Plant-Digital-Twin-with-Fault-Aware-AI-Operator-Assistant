from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import sleep
from typing import Iterator

from wtdt.agent.assistant import recommend_actions
from wtdt.agent.fault_detector import FaultDetection, detect_basic_faults
from wtdt.plc.controller import SimulatedPlc
from wtdt.simulator.process import FaultScenario, PlantState, WaterTreatmentProcess


TagValue = float | bool | str


@dataclass(frozen=True)
class SimulationSnapshot:
    timestamp_utc: str
    sequence: int
    tags: dict[str, TagValue]
    detections: list[FaultDetection] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    @property
    def alarm_active(self) -> bool:
        return bool(self.detections or self.tags.get("alarm_active"))


class SimulationRuntime:
    def __init__(
        self,
        process: WaterTreatmentProcess | None = None,
        plc: SimulatedPlc | None = None,
    ) -> None:
        self.process = process or WaterTreatmentProcess()
        self.plc = plc or SimulatedPlc()
        self.sequence = 0
        self.ph_setpoint = self.plc.ph_setpoint
        self.tank_level_setpoint_pct = self.plc.tank_level_setpoint_pct

    def set_setpoints(
        self,
        *,
        ph_setpoint: float | None = None,
        tank_level_setpoint_pct: float | None = None,
    ) -> None:
        if ph_setpoint is not None:
            self.ph_setpoint = ph_setpoint
        if tank_level_setpoint_pct is not None:
            self.tank_level_setpoint_pct = tank_level_setpoint_pct

    def inject_fault(self, scenario: FaultScenario | str) -> None:
        self.process.inject_fault(scenario)
        if self.plc.state.value == "fault":
            self.plc.reset()

    def clear_fault(self) -> None:
        self.process.clear_fault()
        self.plc.reset()

    def tick(self, seconds: float = 1.0) -> SimulationSnapshot:
        self.sequence += 1
        self.process.step(seconds)
        tags = self.process.read_tags()
        commands = self.plc.scan(
            tank_level_pct=float(tags["tank_level_pct"]),
            reactor_ph=float(tags["reactor_ph"]),
            ph_setpoint=self.ph_setpoint,
            tank_level_setpoint_pct=self.tank_level_setpoint_pct,
            seconds=seconds,
        )
        self.process.apply_controls(
            inlet_pump_cmd=bool(commands["inlet_pump_cmd"]),
            outlet_valve_cmd_pct=float(commands["outlet_valve_cmd_pct"]),
            dosing_pump_cmd_pct=float(commands["dosing_pump_cmd_pct"]),
        )
        tags = self.process.read_tags()
        tags.update(commands)
        tags["simulation_seconds_per_tick"] = seconds
        detections = detect_basic_faults(tags)
        recommendations = recommend_actions(detections)

        if detections:
            tags["alarm_active"] = True

        return SimulationSnapshot(
            timestamp_utc=datetime.now(UTC).isoformat(),
            sequence=self.sequence,
            tags=tags,
            detections=detections,
            recommendations=recommendations,
        )

    def run(
        self,
        *,
        steps: int,
        seconds_per_step: float = 1.0,
        sleep_between_steps: bool = False,
    ) -> Iterator[SimulationSnapshot]:
        for _ in range(steps):
            yield self.tick(seconds=seconds_per_step)
            if sleep_between_steps:
                sleep(seconds_per_step)


def make_demo_runtime(
    *,
    initial_state: PlantState | None = None,
    fault: FaultScenario | str | None = None,
) -> SimulationRuntime:
    runtime = SimulationRuntime(process=WaterTreatmentProcess(initial_state or PlantState()))
    if fault:
        runtime.inject_fault(fault)
    return runtime


def format_snapshot(snapshot: SimulationSnapshot) -> str:
    tags = snapshot.tags
    alarm_codes = ", ".join(detection.code for detection in snapshot.detections) or "none"
    return (
        f"t={snapshot.sequence:03d} "
        f"level={float(tags['tank_level_pct']):5.1f}% "
        f"level_sp={float(tags['tank_level_setpoint_pct']):4.1f}% "
        f"pH={float(tags['reactor_ph']):4.2f} "
        f"pH_sp={float(tags['ph_setpoint']):4.2f} "
        f"plc={tags['plc_state']} "
        f"inlet={_on_off(bool(tags['inlet_pump_cmd']))} "
        f"dose={float(tags['dosing_pump_cmd_pct']):5.1f}% "
        f"outlet={float(tags['outlet_valve_cmd_pct']):5.1f}% "
        f"pid(level={float(tags['level_pid_output_pct']):+5.1f}%, "
        f"pH={float(tags['ph_pid_output_pct']):5.1f}%) "
        f"alarms={alarm_codes}"
    )


def _on_off(value: bool) -> str:
    return "on" if value else "off"
