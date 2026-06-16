from wtdt.agent.fault_detector import FaultDetection


def recommend_action(detection: FaultDetection) -> str:
    if detection.code == "equipment.dosing_pump_failure":
        return (
            "Check dosing pump power, local isolator, and feedback wiring. "
            "Limit influent flow and switch to standby dosing if available."
        )

    if detection.code == "process.ph_excursion":
        return (
            "Verify pH trend and dosing response. Keep the process in supervised mode "
            "and avoid manual overdosing until the trend confirms recovery."
        )

    return "Review alarm evidence, confirm instrument health, and follow site operating procedures."
