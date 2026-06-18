# Architecture

## Overview

The project models a water treatment plant as a complete industrial stack:

```text
Process simulator -> Simulated PLC -> MQTT broker -> Historian
                                      -> Dashboard
                                      -> Fault detector -> AI operator assistant
```

The Step 2 process simulator is visualized in [Process Simulator](process-simulator.md).

## Purdue / ISA-95 Mapping

| Layer | Project component |
| --- | --- |
| Level 0 Field devices | Simulated sensors, actuators, pumps, valves |
| Level 1 Control | Simulated PLC scan cycle, PID, state machine |
| Level 2 Supervisory | Dashboard, alarms, fault injection controls |
| Level 3 Operations | Historian and tag dictionary |
| Level 4 IT / analytics | AI operator assistant and reports |

## Stack Justification

- MQTT is lightweight and widely used in IIoT pipelines.
- Python keeps the simulation and control logic easy to inspect during viva.
- SQLite is reliable for the first historian implementation and can be replaced by InfluxDB later.
- Streamlit provides a quick operator-facing dashboard suitable for a live demo.
- Docker Compose keeps the demo reproducible across laptops.
