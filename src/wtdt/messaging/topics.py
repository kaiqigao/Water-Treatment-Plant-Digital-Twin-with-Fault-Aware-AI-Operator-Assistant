BASE_TOPIC = "tuma206/plant1"
CLOUD_TAG_TOPIC_PREFIX = "plant/tags"

PLANT_STATE_TOPIC = f"{BASE_TOPIC}/plant/state"
PLC_COMMAND_TOPIC = f"{BASE_TOPIC}/plc/command"
ALARM_EVENT_TOPIC = f"{BASE_TOPIC}/alarm/event"
FAULT_INJECTION_TOPIC = f"{BASE_TOPIC}/fault/injection"
HEARTBEAT_TOPIC = f"{BASE_TOPIC}/infra/heartbeat"

TELEMETRY_TOPIC = PLANT_STATE_TOPIC
COMMAND_TOPIC = PLC_COMMAND_TOPIC
ALARM_TOPIC = ALARM_EVENT_TOPIC
FAULT_TOPIC = FAULT_INJECTION_TOPIC

TOPICS = {
    "plant_state": PLANT_STATE_TOPIC,
    "plc_command": PLC_COMMAND_TOPIC,
    "alarm_event": ALARM_EVENT_TOPIC,
    "fault_injection": FAULT_INJECTION_TOPIC,
    "heartbeat": HEARTBEAT_TOPIC,
}


def topic_for(name: str) -> str:
    return TOPICS[name]


def cloud_tag_topic(tag_name: str) -> str:
    normalized = tag_name.strip().replace(" ", "_")
    if not normalized or "/" in normalized:
        raise ValueError(f"invalid cloud tag name: {tag_name!r}")
    return f"{CLOUD_TAG_TOPIC_PREFIX}/{normalized}"
