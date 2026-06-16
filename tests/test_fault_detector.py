from wtdt.agent.fault_detector import detect_basic_faults


def test_detects_dosing_pump_failure() -> None:
    detections = detect_basic_faults({"dosing_pump_cmd_pct": 50.0, "dosing_flow_lpm": 0.0})

    assert any(detection.code == "equipment.dosing_pump_failure" for detection in detections)
