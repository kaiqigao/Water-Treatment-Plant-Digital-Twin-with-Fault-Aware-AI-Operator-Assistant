# Demo Script

## Normal Operation

1. Start the stack.
2. Open the dashboard.
3. Show tank level, pH, PLC state, trends, and historian status.

## Fault Demonstrations

For each fault:

1. Inject the fault from the dashboard.
2. Start timing.
3. Confirm alarm appears within 60 seconds.
4. Confirm AI recommendation appears with evidence.
5. Reset the fault and return to stable operation.

## Fault Order

1. Sensor: pH sensor drift or stuck reading.
2. Equipment: dosing pump fails to start.
3. Process: influent pH excursion.
4. Infrastructure: historian write failure.

## Viva Preparation

Each team member should be able to explain:

- Why this stack was chosen.
- How the PLC scan cycle works.
- How each fault is injected and detected.
- How the assistant generates safe recommendations.
- How to reproduce the demo from the README.
