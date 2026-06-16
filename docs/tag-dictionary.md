# Tag Dictionary

| Tag | Type | Unit | Source | Description |
| --- | --- | --- | --- | --- |
| plant/unit1/tank/level_pct | float | % | simulator | Reactor tank level |
| plant/unit1/ph/reactor_ph | float | pH | simulator | Measured reactor pH |
| plant/unit1/ph/ph_setpoint | float | pH | PLC | pH control setpoint |
| plant/unit1/flow/influent_lpm | float | L/min | simulator | Influ​ent flow |
| plant/unit1/flow/effluent_lpm | float | L/min | simulator | Effluent flow |
| plant/unit1/pump/inlet/cmd | bool | - | PLC | Inlet pump command |
| plant/unit1/pump/inlet/feedback | bool | - | simulator | Inlet pump feedback |
| plant/unit1/pump/dosing/cmd_pct | float | % | PLC | Chemical dosing pump command |
| plant/unit1/pump/dosing/flow_lpm | float | L/min | simulator | Chemical dosing feedback flow |
| plant/unit1/valve/outlet/cmd_pct | float | % | PLC | Outlet valve command |
| plant/unit1/plc/state | string | - | PLC | Current PLC state |
| plant/unit1/alarm/active | bool | - | fault detector | Whether any alarm is active |
| plant/unit1/infra/mqtt/heartbeat | int | count | services | MQTT heartbeat |
| plant/unit1/infra/historian/write_ok | bool | - | historian | Historian write status |
