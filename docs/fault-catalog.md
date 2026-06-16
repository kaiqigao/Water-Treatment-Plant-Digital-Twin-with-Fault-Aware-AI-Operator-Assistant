# Fault Catalog

The assignment requires one implemented fault per layer.

## Sensor Layer

- Fault: pH sensor drift or stuck reading.
- Detection: compare measured pH against process expectation and dosing response trend.
- Alarm target: detect and alert within 60 seconds.
- Operator recommendation: verify sensor calibration, use redundant estimate, and avoid unsafe automatic dosing.

## Equipment Layer

- Fault: chemical dosing pump fails to start.
- Detection: command-vs-feedback mismatch. Pump command is active but dosing flow remains zero.
- Alarm target: detect and alert within 60 seconds.
- Operator recommendation: check pump power, isolator, feedback wiring, and switch to standby pump if available.

## Process Layer

- Fault: influent pH excursion.
- Detection: pH deviates from setpoint and trend continues outside normal range.
- Alarm target: detect and alert within 60 seconds.
- Operator recommendation: limit influent, supervise dosing, and monitor recovery trend.

## Infrastructure Layer

- Fault: historian write failure.
- Detection: historian write status is false or latest stored timestamp is stale.
- Alarm target: detect and alert within 60 seconds.
- Operator recommendation: distinguish data outage from process alarm, check historian service and disk path.
