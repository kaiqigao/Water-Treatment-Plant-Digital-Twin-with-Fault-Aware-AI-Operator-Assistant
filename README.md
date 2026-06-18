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

## Demo Goal

During the demo, the dashboard should show normal plant operation, allow controlled fault injection, and display alarms plus assistant recommendations within 60 seconds.

See:

- [Architecture](docs/architecture.md)
- [Process Simulator](docs/process-simulator.md)
- [Tag Dictionary](docs/tag-dictionary.md)
- [Fault Catalog](docs/fault-catalog.md)
- [Demo Script](docs/demo-script.md)
