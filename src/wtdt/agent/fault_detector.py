from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class FaultDetection:
    code: str
    severity: str
    evidence: list[str]


def detect_basic_faults(tags: dict[str, float | bool | str]) -> list[FaultDetection]:
    detections: list[FaultDetection] = []

    dosing_cmd_pct = _float_tag(tags, "dosing_pump_cmd_pct")
    dosing_flow_lpm = _float_tag(tags, "dosing_flow_lpm")
    if dosing_cmd_pct >= 5.0 and dosing_flow_lpm <= 0.05:
        detections.append(
            FaultDetection(
                code="equipment.dosing_pump_failure",
                severity="high",
                evidence=[
                    f"Dosing command is {dosing_cmd_pct:.1f}% but flow feedback is "
                    f"{dosing_flow_lpm:.2f} L/min."
                ],
            )
        )

    outlet_cmd_pct = _float_tag(tags, "outlet_valve_cmd_pct")
    effluent_flow_lpm = _float_tag(tags, "effluent_flow_lpm")
    if outlet_cmd_pct >= 20.0 and effluent_flow_lpm <= 0.05:
        detections.append(
            FaultDetection(
                code="equipment.outlet_valve_stuck",
                severity="high",
                evidence=[
                    f"Outlet valve command is {outlet_cmd_pct:.1f}% but effluent flow is "
                    f"{effluent_flow_lpm:.2f} L/min."
                ],
            )
        )

    reactor_ph = _float_tag(tags, "reactor_ph", 7.0)
    if reactor_ph < 6.2 or reactor_ph > 7.8:
        detections.append(
            FaultDetection(
                code="process.ph_excursion",
                severity="medium",
                evidence=[f"Reactor pH is outside normal range: {reactor_ph:.2f}."],
            )
        )

    tank_level_pct = _float_tag(tags, "tank_level_pct", 50.0)
    if tank_level_pct < 15.0 or tank_level_pct > 92.0:
        detections.append(
            FaultDetection(
                code="process.tank_level_excursion",
                severity="medium",
                evidence=[f"Tank level is outside normal operating band: {tank_level_pct:.1f}%."],
            )
        )

    active_fault = str(tags.get("active_fault", ""))
    if active_fault == "process.ph_shock":
        detections.append(
            FaultDetection(
                code="process.ph_shock",
                severity="medium",
                evidence=["Influent pH shock fault is active in the process layer."],
            )
        )

    if active_fault == "process.influent_surge":
        detections.append(
            FaultDetection(
                code="process.influent_surge",
                severity="medium",
                evidence=["Influent surge fault is active in the process layer."],
            )
        )

    actual_ph = _optional_float_tag(tags, "actual_reactor_ph")
    if actual_ph is not None and abs(actual_ph - reactor_ph) >= 0.5:
        detections.append(
            FaultDetection(
                code="sensor.ph_drift",
                severity="high",
                evidence=[
                    f"Measured pH differs from process estimate by {abs(actual_ph - reactor_ph):.2f}."
                ],
            )
        )

    if active_fault == "sensor.ph_stuck":
        detections.append(
            FaultDetection(
                code="sensor.ph_stuck",
                severity="high",
                evidence=["pH sensor reading is marked as stuck by the injection layer."],
            )
        )

    if tags.get("mqtt_connected") is False:
        detections.append(
            FaultDetection(
                code="infrastructure.mqtt_disconnected",
                severity="medium",
                evidence=["MQTT connectivity tag is false."],
            )
        )

    if tags.get("historian_write_ok") is False:
        detections.append(
            FaultDetection(
                code="infrastructure.historian_write_failed",
                severity="medium",
                evidence=["Historian write status is false."],
            )
        )

    return detections


def _float_tag(tags: dict[str, float | bool | str], name: str, default: float = 0.0) -> float:
    value = tags.get(name, default)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if isfinite(number) else default


def _optional_float_tag(tags: dict[str, float | bool | str], name: str) -> float | None:
    if name not in tags:
        return None
    value = _float_tag(tags, name)
    return value
