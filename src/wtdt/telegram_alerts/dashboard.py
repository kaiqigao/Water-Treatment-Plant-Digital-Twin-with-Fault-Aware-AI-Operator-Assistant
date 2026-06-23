from wtdt.runtime import SimulationSnapshot
from wtdt.telegram_alerts.mqtt_source import AlarmEvent


def alarm_events_from_snapshot(snapshot: SimulationSnapshot) -> list[AlarmEvent]:
    return [
        AlarmEvent(
            code=detection.code,
            severity=detection.severity,
            evidence=detection.evidence,
            recommendation=recommendation,
            timestamp_utc=snapshot.timestamp_utc,
            sequence=snapshot.sequence,
        )
        for detection, recommendation in zip(
            snapshot.detections,
            snapshot.recommendations,
            strict=True,
        )
    ]

