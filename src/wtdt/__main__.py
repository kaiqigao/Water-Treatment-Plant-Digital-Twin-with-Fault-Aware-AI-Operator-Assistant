import argparse
from pathlib import Path

from wtdt.historian.store import SQLiteHistorian
from wtdt.messaging.publisher import MqttTelemetryPublisher
from wtdt.runtime import SimulationSnapshot, format_snapshot, make_demo_runtime
from wtdt.simulator.process import FaultScenario


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--ph-setpoint", type=float)
    parser.add_argument("--tank-level-setpoint", type=float)
    parser.add_argument("--sleep", action="store_true")
    parser.add_argument("--fault", choices=[scenario.value for scenario in FaultScenario])
    parser.add_argument("--mqtt", action="store_true")
    parser.add_argument("--mqtt-host", default="localhost")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--historian-path", type=Path)
    args = parser.parse_args(argv)

    runtime = make_demo_runtime(fault=args.fault)
    runtime.set_setpoints(
        ph_setpoint=args.ph_setpoint,
        tank_level_setpoint_pct=args.tank_level_setpoint,
    )
    publisher = _make_publisher(args.mqtt, args.mqtt_host, args.mqtt_port)
    historian = SQLiteHistorian(args.historian_path) if args.historian_path else None

    try:
        for snapshot in runtime.run(
            steps=args.steps,
            seconds_per_step=args.interval * args.speed,
            sleep_between_steps=args.sleep,
        ):
            if historian:
                historian.write_snapshot(snapshot)
            if publisher:
                publisher.publish_snapshot(snapshot)
            print(format_snapshot(snapshot))
            _print_recommendations(snapshot)
    finally:
        if publisher:
            publisher.close()
        if historian:
            historian.close()


def _make_publisher(
    enabled: bool,
    host: str,
    port: int,
) -> MqttTelemetryPublisher | None:
    if not enabled:
        return None
    publisher = MqttTelemetryPublisher(host=host, port=port)
    publisher.connect()
    return publisher


def _print_recommendations(snapshot: SimulationSnapshot) -> None:
    for detection, recommendation in zip(snapshot.detections, snapshot.recommendations, strict=True):
        print(f"  alarm {detection.severity} {detection.code}: {recommendation}")


if __name__ == "__main__":
    main()
