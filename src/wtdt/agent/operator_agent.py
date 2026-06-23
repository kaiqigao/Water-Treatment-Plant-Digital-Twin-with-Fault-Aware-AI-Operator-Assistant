from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import TYPE_CHECKING

from wtdt.agent.assistant import recommend_action
from wtdt.agent.fault_detector import FaultDetection, detect_basic_faults

if TYPE_CHECKING:
    from wtdt.runtime import SimulationSnapshot, TagValue


@dataclass(frozen=True)
class OperatorDiagnosis:
    state: str
    severity: str
    summary: str
    evidence: list[str] = field(default_factory=list)
    likely_causes: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    safety_note: str = (
        "Keep PLC control and field operation under human supervision. Do not change dosing, "
        "valves, pumps, or electrical equipment without site approval."
    )

    @property
    def alarm_active(self) -> bool:
        return self.state == "alarm"

    def as_text(self) -> str:
        lines = [
            f"State: {self.state.upper()}",
            f"Severity: {self.severity}",
            f"Summary: {self.summary}",
        ]
        lines.extend(_section("Evidence", self.evidence))
        lines.extend(_section("Likely causes", self.likely_causes))
        lines.extend(_section("Checks", self.checks))
        lines.extend(_section("Actions", self.actions))
        lines.append(f"Safety: {self.safety_note}")
        return "\n".join(lines)


def diagnose_snapshot(
    snapshot: SimulationSnapshot,
    recent_snapshots: list[SimulationSnapshot] | None = None,
) -> OperatorDiagnosis:
    recent_tags = [sample.tags for sample in recent_snapshots or []]
    if snapshot.tags not in recent_tags:
        recent_tags.append(snapshot.tags)
    return diagnose_tags(
        snapshot.tags,
        detections=snapshot.detections,
        recent_tags=recent_tags,
    )


def diagnose_tags(
    tags: dict[str, TagValue],
    *,
    detections: list[FaultDetection] | None = None,
    recent_tags: list[dict[str, TagValue]] | None = None,
) -> OperatorDiagnosis:
    active_detections = detections if detections is not None else detect_basic_faults(tags)
    if not active_detections:
        return _clear_diagnosis(tags, recent_tags or [tags])

    highest = _highest_severity(active_detections)
    evidence = _plant_evidence(tags, recent_tags or [tags])
    likely_causes: list[str] = []
    checks: list[str] = []
    actions: list[str] = []

    for detection in active_detections:
        evidence.extend(detection.evidence)
        playbook = _playbook_for(detection.code)
        likely_causes.extend(playbook.likely_causes)
        checks.extend(playbook.checks)
        actions.append(recommend_action(detection))

    codes = ", ".join(detection.code for detection in active_detections)
    return OperatorDiagnosis(
        state="alarm",
        severity=highest,
        summary=f"Active abnormal condition detected: {codes}.",
        evidence=_unique(evidence),
        likely_causes=_unique(likely_causes),
        checks=_unique(checks),
        actions=_unique(actions),
    )


@dataclass(frozen=True)
class _Playbook:
    likely_causes: list[str]
    checks: list[str]


def _clear_diagnosis(
    tags: dict[str, TagValue],
    recent_tags: list[dict[str, TagValue]],
) -> OperatorDiagnosis:
    evidence = _plant_evidence(tags, recent_tags)
    evidence.append("No active fault detections are present.")
    return OperatorDiagnosis(
        state="clear",
        severity="none",
        summary="Plant is running within the current rule-based operating envelope.",
        evidence=_unique(evidence),
        likely_causes=["No immediate abnormal cause is indicated by the current tags."],
        checks=[
            "Continue normal trend monitoring for pH, tank level, dosing flow, and historian status.",
            "Confirm the displayed values match field instruments during routine rounds.",
        ],
        actions=["No operator intervention is required at this time."],
        safety_note="Maintain routine supervision and follow the site operating procedure.",
    )


def _playbook_for(code: str) -> _Playbook:
    if code in {"sensor.ph_drift", "sensor.ph_stuck"}:
        return _Playbook(
            likely_causes=[
                "pH probe fouling, calibration drift, transmitter issue, or stale sensor signal.",
                "Automatic dosing may be responding to an unreliable measurement.",
            ],
            checks=[
                "Compare online pH with a grab sample or portable meter.",
                "Inspect probe condition, cleaning status, calibration date, and signal wiring.",
                "Review whether dosing changed while the measured pH remained flat or offset.",
            ],
        )

    if code == "equipment.dosing_pump_failure":
        return _Playbook(
            likely_causes=[
                "Dosing pump is commanded but no flow feedback is reaching the process.",
                "Possible power, local isolator, suction blockage, empty chemical tank, or feedback fault.",
            ],
            checks=[
                "Check pump power, run indication, local isolator, suction line, and dosing tank level.",
                "Compare command percentage with local pump feedback and flow indication.",
                "Verify standby dosing availability before increasing manual intervention.",
            ],
        )

    if code == "equipment.outlet_valve_stuck":
        return _Playbook(
            likely_causes=[
                "Outlet valve or actuator is not following PLC command.",
                "Position feedback, air supply, actuator power, or downstream blockage may be faulty.",
            ],
            checks=[
                "Confirm outlet valve local position and actuator status.",
                "Check effluent flow path, downstream isolation, and position feedback wiring.",
                "Watch tank level trend for a high-level escalation.",
            ],
        )

    if code in {"process.ph_excursion", "process.ph_shock"}:
        return _Playbook(
            likely_causes=[
                "Influent chemistry changed faster than the dosing loop can correct.",
                "Dosing control may be limited, delayed, or based on a questionable pH reading.",
            ],
            checks=[
                "Review influent pH, reactor pH trend, dosing command, and dosing flow together.",
                "Confirm chemical strength and safe dosing limits before any manual correction.",
                "Check for upstream batch discharge or recent process disturbance.",
            ],
        )

    if code in {"process.influent_surge", "process.tank_level_excursion"}:
        return _Playbook(
            likely_causes=[
                "Influent flow and outlet capacity are not balanced.",
                "Tank level may move outside the normal operating band if the surge continues.",
            ],
            checks=[
                "Compare influent flow, effluent flow, inlet command, outlet command, and tank level trend.",
                "Check upstream pump operation and downstream discharge availability.",
                "Prepare supervised flow limiting if level approaches alarm limits.",
            ],
        )

    if code == "infrastructure.mqtt_disconnected":
        return _Playbook(
            likely_causes=[
                "Telemetry path to the MQTT broker is unavailable or unhealthy.",
                "The process may still be locally controlled while remote visibility is degraded.",
            ],
            checks=[
                "Check broker reachability, network status, and local PLC/dashboard connectivity.",
                "Confirm whether field instruments remain normal before treating it as a process fault.",
            ],
        )

    if code == "infrastructure.historian_write_failed":
        return _Playbook(
            likely_causes=[
                "Historian storage path, database permissions, or disk availability may be failing.",
                "Trend and audit data may be incomplete until storage is restored.",
            ],
            checks=[
                "Check database path, disk capacity, write permissions, and service logs.",
                "Continue live monitoring while restoring reliable trend storage.",
            ],
        )

    return _Playbook(
        likely_causes=["The alarm code is not in the detailed playbook."],
        checks=["Review alarm evidence, field instruments, and site operating procedures."],
    )


def _plant_evidence(
    tags: dict[str, TagValue],
    recent_tags: list[dict[str, TagValue]],
) -> list[str]:
    evidence = [
        f"Tank level {float(tags.get('tank_level_pct', 0.0)):.1f}%, "
        f"reactor pH {float(tags.get('reactor_ph', 0.0)):.2f}.",
        f"Influent {float(tags.get('influent_flow_lpm', 0.0)):.1f} L/min, "
        f"effluent {float(tags.get('effluent_flow_lpm', 0.0)):.1f} L/min, "
        f"dosing flow {float(tags.get('dosing_flow_lpm', 0.0)):.2f} L/min.",
    ]
    trend = _trend_summary(recent_tags)
    if trend:
        evidence.append(trend)
    active_fault = str(tags.get("active_fault") or "")
    if active_fault:
        evidence.append(f"Injected fault marker is active: {active_fault}.")
    return evidence


def _trend_summary(recent_tags: list[dict[str, TagValue]]) -> str:
    if len(recent_tags) < 2:
        return ""
    first = recent_tags[0]
    last = recent_tags[-1]
    level_delta = float(last.get("tank_level_pct", 0.0)) - float(first.get("tank_level_pct", 0.0))
    ph_delta = float(last.get("reactor_ph", 0.0)) - float(first.get("reactor_ph", 0.0))
    dosing_values = [
        float(tags.get("dosing_flow_lpm", 0.0))
        for tags in recent_tags
        if isinstance(tags.get("dosing_flow_lpm", 0.0), (float, int))
    ]
    dosing_avg = mean(dosing_values) if dosing_values else 0.0
    return (
        f"Recent trend: level changed {level_delta:+.1f} percentage points, "
        f"pH changed {ph_delta:+.2f}, average dosing flow {dosing_avg:.2f} L/min."
    )


def _highest_severity(detections: list[FaultDetection]) -> str:
    order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    return max((detection.severity for detection in detections), key=lambda item: order.get(item, 0))


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _section(title: str, items: list[str]) -> list[str]:
    if not items:
        return []
    return [f"{title}:"] + [f"- {item}" for item in items]
