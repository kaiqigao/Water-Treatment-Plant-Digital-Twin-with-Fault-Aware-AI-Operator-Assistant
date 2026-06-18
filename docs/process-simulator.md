# Process Simulator

This page visualizes the Step 2 process simulator implementation.

## Process Model

```mermaid
flowchart LR
    PLC["PLC commands"] --> Controls["apply_controls()"]
    Controls --> Influent["influent_flow_lpm"]
    Controls --> Effluent["effluent_flow_lpm"]
    Controls --> Dosing["dosing_flow_lpm"]

    Influent --> Step["step(seconds)"]
    Effluent --> Step
    Dosing --> Step

    Step --> Level["tank_level_pct"]
    Step --> PH["reactor_ph"]
    Step --> Limits["range limits"]

    Limits --> State["PlantState"]
    State --> PLC
```

## State Update Logic

```mermaid
flowchart TD
    Start["Start with PlantState"] --> ClampInputs["Clamp current state values"]
    ClampInputs --> Balance["flow balance = influent - effluent"]
    Balance --> LevelDelta["level delta = balance * seconds / 60 / tank volume"]
    LevelDelta --> UpdateLevel["update tank_level_pct"]

    ClampInputs --> Mix["mix reactor pH toward influent pH"]
    Mix --> Dose["add dosing pH effect"]
    Dose --> UpdatePH["update reactor_ph"]

    UpdateLevel --> ClampOutputs["Clamp outputs to physical ranges"]
    UpdatePH --> ClampOutputs
    ClampOutputs --> Done["Return PlantState"]
```

## Key Ranges

| Value | Range | Why it matters |
| --- | --- | --- |
| `tank_level_pct` | 0 to 100% | Prevents impossible tank levels. |
| `reactor_ph` | 0 to 14 | Keeps pH in a valid physical range. |
| `influent_flow_lpm` | 0 to configured max | Simulates inlet pump capacity. |
| `effluent_flow_lpm` | 0 to configured max | Simulates outlet valve capacity. |
| `dosing_flow_lpm` | 0 to configured max | Simulates dosing pump capacity. |

## Test Coverage

```mermaid
flowchart LR
    Tests["tests/test_process.py"] --> Rise["Influent > effluent raises level"]
    Tests --> Fall["Effluent > influent lowers level"]
    Tests --> DoseTest["Dosing raises pH gradually"]
    Tests --> LimitsTest["Invalid values are clamped"]
    Tests --> ControlsTest["PLC commands map to flows"]
```
