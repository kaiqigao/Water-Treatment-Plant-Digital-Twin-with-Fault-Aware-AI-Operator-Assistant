import argparse
import logging
import os
from threading import Lock
from time import sleep

from wtdt.messaging.topics import ALARM_EVENT_TOPIC
from wtdt.telegram_alerts.gate import AlarmGate
from wtdt.telegram_alerts.mqtt_source import AlarmEvent, MqttAlarmSubscriber
from wtdt.telegram_alerts.sender import TelegramSender

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Forward WTdT alarm events to Telegram.")
    parser.add_argument("--mqtt-host", default=os.getenv("MQTT_HOST", "localhost"))
    parser.add_argument("--mqtt-port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--topic", default=os.getenv("ALARM_EVENT_TOPIC", ALARM_EVENT_TOPIC))
    parser.add_argument("--telegram-token", default=os.getenv("TELEGRAM_BOT_TOKEN", ""))
    parser.add_argument("--chat-id", default=os.getenv("TELEGRAM_CHAT_ID", ""))
    parser.add_argument("--dry-run", action="store_true", default=_truthy(os.getenv("DRY_RUN", "true")))
    parser.add_argument(
        "--throttle-s",
        type=float,
        default=float(os.getenv("TELEGRAM_THROTTLE_S", "60.0")),
    )
    parser.add_argument(
        "--clear-after-s",
        type=float,
        default=float(os.getenv("TELEGRAM_CLEAR_AFTER_S", "5.0")),
    )
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
    )

    gate = AlarmGate(throttle_s=args.throttle_s, clear_after_s=args.clear_after_s)
    sender = TelegramSender(
        token=args.telegram_token,
        chat_id=args.chat_id,
        dry_run=args.dry_run,
    )
    lock = Lock()

    def on_alarm(event: AlarmEvent) -> None:
        with lock:
            should_send = gate.observe(event.code)
        if not should_send:
            log.debug("suppressed repeated alarm: %s", event.code)
            return

        message = format_alarm_message(event)
        if sender.send(message):
            log.info("telegram alert sent: %s", event.code)
        else:
            log.warning("telegram alert failed: %s", event.code)

    subscriber = MqttAlarmSubscriber(
        host=args.mqtt_host,
        port=args.mqtt_port,
        topic=args.topic,
        on_alarm=on_alarm,
    )
    subscriber.connect()
    print(
        "telegram alerts running: "
        f"mqtt={args.mqtt_host}:{args.mqtt_port} "
        f"topic={args.topic} "
        f"dry_run={args.dry_run}"
    )

    try:
        while True:
            sleep(0.5)
            with lock:
                gate.expire()
    except KeyboardInterrupt:
        print("telegram alerts stopped")
    finally:
        subscriber.close()


def format_alarm_message(event: AlarmEvent) -> str:
    lines = [
        f"[ALARM] {event.code}",
        f"severity: {event.severity}",
    ]
    if event.timestamp_utc:
        lines.append(f"time: {event.timestamp_utc}")
    if event.sequence is not None:
        lines.append(f"sequence: {event.sequence}")
    for item in event.evidence:
        lines.append(f"evidence: {item}")
    if event.recommendation:
        lines.append(f"recommendation: {event.recommendation}")
    return "\n".join(lines)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    main()

