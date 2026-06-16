from dataclasses import dataclass


@dataclass(frozen=True)
class FaultDetection:
    code: str
    severity: str
    evidence: list[str]


def detect_basic_faults(tags: dict[str, float | bool | str]) -> list[FaultDetection]:
    detections: list[FaultDetection] = []

    if tags.get("dosing_pump_cmd_pct", 0.0) and tags.get("dosing_flow_lpm", 0.0) == 0.0:
        detections.append(
            FaultDetection(
                code="equipment.dosing_pump_failure",
                severity="high",
                evidence=["Dosing pump command is active but dosing flow feedback is zero."],
            )
        )

    reactor_ph = float(tags.get("reactor_ph", 7.0))
    if reactor_ph < 6.2 or reactor_ph > 7.8:
        detections.append(
            FaultDetection(
                code="process.ph_excursion",
                severity="medium",
                evidence=[f"Reactor pH is outside normal range: {reactor_ph:.2f}."],
            )
        )

    return detections
