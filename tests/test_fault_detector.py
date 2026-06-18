from wtdt.agent.fault_detector import detect_basic_faults


def test_detects_dosing_pump_failure() -> None:
    detections = detect_basic_faults({"dosing_pump_cmd_pct": 50.0, "dosing_flow_lpm": 0.0})

    assert any(detection.code == "equipment.dosing_pump_failure" for detection in detections)


def test_detects_sensor_ph_drift() -> None:
    detections = detect_basic_faults({"reactor_ph": 7.7, "actual_reactor_ph": 6.8})

    assert any(detection.code == "sensor.ph_drift" for detection in detections)


def test_detects_infrastructure_mqtt_disconnect() -> None:
    detections = detect_basic_faults({"mqtt_connected": False})

    assert any(detection.code == "infrastructure.mqtt_disconnected" for detection in detections)


def test_detects_injected_process_faults_immediately() -> None:
    ph_shock = detect_basic_faults({"active_fault": "process.ph_shock"})
    surge = detect_basic_faults({"active_fault": "process.influent_surge"})

    assert any(detection.code == "process.ph_shock" for detection in ph_shock)
    assert any(detection.code == "process.influent_surge" for detection in surge)
