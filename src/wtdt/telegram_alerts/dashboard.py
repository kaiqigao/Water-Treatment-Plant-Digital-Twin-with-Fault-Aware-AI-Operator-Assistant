from wtdt.runtime import SimulationSnapshot
from wtdt.agent.operator_agent import diagnose_snapshot
from wtdt.telegram_alerts.mqtt_source import AlarmEvent


def alarm_events_from_snapshot(snapshot: SimulationSnapshot) -> list[AlarmEvent]:
    diagnosis = diagnose_snapshot(snapshot)
    return [
        AlarmEvent(
            code=detection.code,
            severity=detection.severity,
            evidence=detection.evidence,
            recommendation=recommendation,
            summary=diagnosis.summary,
            checks=diagnosis.checks[:3],
            actions=diagnosis.actions[:3],
            timestamp_utc=snapshot.timestamp_utc,
            sequence=snapshot.sequence,
        )
        for detection, recommendation in zip(
            snapshot.detections,
            snapshot.recommendations,
            strict=True,
        )
    ]
