from wtdt.agent.fault_detector import FaultDetection


def recommend_action(detection: FaultDetection) -> str:
    if detection.code == "sensor.ph_drift":
        return (
            "Verify pH probe calibration against a grab sample. Hold automatic dosing changes "
            "until the measurement is trusted."
        )

    if detection.code == "sensor.ph_stuck":
        return (
            "Treat the pH value as unreliable, inspect the probe and transmitter, and run the "
            "plant on supervised fallback limits."
        )

    if detection.code == "equipment.dosing_pump_failure":
        return (
            "Check dosing pump power, local isolator, and feedback wiring. "
            "Limit influent flow and switch to standby dosing if available."
        )

    if detection.code == "equipment.outlet_valve_stuck":
        return (
            "Check the outlet valve actuator and position feedback. Stop filling if level is "
            "rising and prepare manual bypass or maintenance isolation."
        )

    if detection.code == "process.ph_excursion":
        return (
            "Verify pH trend and dosing response. Keep the process in supervised mode "
            "and avoid manual overdosing until the trend confirms recovery."
        )

    if detection.code == "process.ph_shock":
        return (
            "Reduce or isolate the disturbed influent stream, monitor pH recovery, and keep "
            "dosing under operator supervision."
        )

    if detection.code == "process.influent_surge":
        return (
            "Check upstream flow conditions, supervise inlet pumping, and use discharge control "
            "to prevent a high-level excursion."
        )

    if detection.code == "process.tank_level_excursion":
        return (
            "Confirm inlet and outlet flows, keep the PLC in supervised mode, and stabilize the "
            "level before returning to normal operation."
        )

    if detection.code == "infrastructure.mqtt_disconnected":
        return (
            "Distinguish telemetry outage from a process alarm. Check broker reachability and "
            "keep local PLC control active."
        )

    if detection.code == "infrastructure.historian_write_failed":
        return (
            "Check database path and disk permissions. Continue local monitoring while trend "
            "storage is restored."
        )

    return "Review alarm evidence, confirm instrument health, and follow site operating procedures."


def recommend_actions(detections: list[FaultDetection]) -> list[str]:
    return [recommend_action(detection) for detection in detections]
