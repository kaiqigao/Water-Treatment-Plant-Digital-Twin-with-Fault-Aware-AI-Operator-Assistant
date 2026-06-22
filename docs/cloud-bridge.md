# Cloud Bridge

This project includes a ThingsBoard bridge that follows the TUMA206 reference pattern:

```text
WTdT simulator -> local Mosquitto -> wtdt.cloud_bridge -> ThingsBoard Cloud
```

The simulator remains decoupled from the cloud. It publishes every numeric process and PLC tag to
the local broker under:

```text
plant/tags/<TAG_NAME>
```

Each message uses the reference payload shape:

```json
{"v": 72.4, "t": 1718712345.6}
```

## Configuration

Copy `.env.example` to `.env` and set:

```text
TB_TOKEN=<ThingsBoard device access token>
TB_HOST=mqtt.thingsboard.cloud
TB_PORT=1883
FLUSH_INTERVAL_S=1.0
```

Do not commit `.env`; it contains the device bearer token.

## Run With Docker Compose

```bash
docker compose --profile cloud up --build
```

The `cloud-bridge` service is behind the `cloud` profile so normal local demos do not require a
ThingsBoard token.

## Run Locally

Start Mosquitto first, then run two terminals:

```bash
python -m wtdt --mqtt --steps 600 --sleep
python -m wtdt.cloud_bridge.main
```

Use `--dry-run` to verify local subscription and batching without sending telemetry to ThingsBoard.

## Viva Talking Points

- The simulated PLC publishes only to local Mosquitto, not directly to the cloud.
- The bridge subscribes to `plant/tags/#`, so new numeric tags appear automatically.
- Batching reduces cloud ingest pressure and matches free-tier dashboard needs.
- ThingsBoard authenticates the bridge using the device access token as the MQTT username.
- In a production plant, this bridge would sit in a Level 3.5 DMZ with TLS and a tag whitelist.
