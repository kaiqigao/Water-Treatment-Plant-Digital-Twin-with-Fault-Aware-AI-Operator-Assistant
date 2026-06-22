import argparse
import os
from time import sleep

from wtdt.cloud_bridge.batcher import TagBatcher
from wtdt.cloud_bridge.local_sub import LocalTagSubscriber
from wtdt.cloud_bridge.tb_pub import ThingsBoardPublisher


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Forward local WTdT MQTT tags to ThingsBoard Cloud.")
    parser.add_argument("--local-host", default=os.getenv("LOCAL_MQTT_HOST", "localhost"))
    parser.add_argument("--local-port", type=int, default=int(os.getenv("LOCAL_MQTT_PORT", "1883")))
    parser.add_argument("--tb-host", default=os.getenv("TB_HOST", "mqtt.thingsboard.cloud"))
    parser.add_argument("--tb-port", type=int, default=int(os.getenv("TB_PORT", "1883")))
    parser.add_argument("--tb-token", default=os.getenv("TB_TOKEN", ""))
    parser.add_argument("--flush-interval", type=float, default=float(os.getenv("FLUSH_INTERVAL_S", "1.0")))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    batcher = TagBatcher()
    subscriber = LocalTagSubscriber(
        host=args.local_host,
        port=args.local_port,
        on_tag=batcher.record,
    )
    publisher = None
    if not args.dry_run:
        publisher = ThingsBoardPublisher(token=args.tb_token, host=args.tb_host, port=args.tb_port)

    subscriber.connect()
    if publisher:
        publisher.connect()

    print(
        "cloud bridge running: "
        f"local={args.local_host}:{args.local_port} "
        f"topic={subscriber.topic_filter} "
        f"thingsboard={args.tb_host}:{args.tb_port} "
        f"dry_run={args.dry_run}"
    )

    try:
        while True:
            sleep(args.flush_interval)
            payload = batcher.flush()
            if not payload:
                continue
            if publisher:
                publisher.publish(payload)
            print(f"published {len(payload['values'])} tags")
    except KeyboardInterrupt:
        print("cloud bridge stopped")
    finally:
        subscriber.close()
        if publisher:
            publisher.close()


if __name__ == "__main__":
    main()
