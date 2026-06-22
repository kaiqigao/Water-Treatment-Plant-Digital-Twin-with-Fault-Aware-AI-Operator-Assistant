# Water Treatment Plant Digital Twin

Group assignment scaffold for TUMA206 Modern Developments in Industry.

This project will implement a working digital twin of a water treatment plant with a simulated PLC, MQTT messaging, historian, operator dashboard, fault injection, and an AI operator assistant.

## Assignment Targets

- Simulate tanks, pumps, valves, level sensors, pH sensors, and chemical dosing.
- Implement deterministic PLC control logic: on/off control, PID, and a state machine.
- Publish a complete tag stream through MQTT.
- Record process data in a historian.
- Display live plant state, trends, and alarms on an operator dashboard.
- Inject one fault in each layer: sensor, equipment, process, and infrastructure.
- Detect, alert, and recommend operator action within 60 seconds of each fault.

## Proposed Stack

- Python for the simulator, PLC, fault detection, and assistant logic.
- Eclipse Mosquitto for MQTT messaging.
- SQLite as the initial lightweight historian, with an easy path to InfluxDB.
- Streamlit for the operator dashboard.
- ThingsBoard Cloud bridge for L3.5 -> L4 telemetry forwarding.
- Docker Compose for reproducible local startup.

## Repository Structure

```text
.
├── config/                 # Runtime configuration
├── docs/                   # Architecture, tag dictionary, fault catalog, demo script
├── slides/                 # Presentation deck source/export
├── src/wtdt/
│   ├── agent/              # Fault detector and operator assistant
│   ├── dashboard/          # Operator dashboard
│   ├── cloud_bridge/       # Local MQTT tag stream -> ThingsBoard Cloud bridge
│   ├── historian/          # Time-series writer and query helpers
│   ├── messaging/          # MQTT topics, publisher, subscriber helpers
│   ├── plc/                # PLC scan cycle, state machine, PID
│   └── simulator/          # Plant process, sensors, actuators, fault injection
└── tests/                  # Unit and integration tests
```

## Quick Start

The current repository is a project skeleton. The implementation will be filled in module by module.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m wtdt
```

## ThingsBoard Cloud Bridge

The simulator publishes a ThingsBoard-compatible tag stream whenever MQTT is enabled:

```text
Topic: plant/tags/<TAG_NAME>
Payload: {"v": <float>, "t": <unix_seconds_float>}
```

To forward those tags to ThingsBoard Cloud:

1. Create a ThingsBoard device and copy its access token.
2. Copy `.env.example` to `.env`.
3. Set `TB_TOKEN` in `.env`.
4. Run the simulator and bridge:

```bash
docker compose --profile cloud up --build
```

For a local dry run without publishing to ThingsBoard:

```bash
python -m wtdt --mqtt --steps 60 --sleep
python -m wtdt.cloud_bridge.main --dry-run
```

The bridge follows the TUMA206 reference pattern: the PLC/simulator only publishes to the local
Mosquitto broker, and a separate bridge process forwards batched telemetry upward to the cloud.

## Demo Goal

During the demo, the dashboard should show normal plant operation, allow controlled fault injection, and display alarms plus assistant recommendations within 60 seconds.

See:

- [Architecture](docs/architecture.md)
- [Cloud Bridge](docs/cloud-bridge.md)
- [Process Simulator](docs/process-simulator.md)
- [Tag Dictionary](docs/tag-dictionary.md)
- [Fault Catalog](docs/fault-catalog.md)
- [Demo Script](docs/demo-script.md)
