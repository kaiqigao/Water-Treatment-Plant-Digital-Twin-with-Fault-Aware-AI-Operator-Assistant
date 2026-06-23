# Operator Agent Integration

## Current role

The project now includes an operator-facing diagnostic agent on top of the deterministic simulator,
PLC, fault detector, dashboard, historian, MQTT stream, and Telegram alerts.

The agent is intentionally advisory. It explains alarms, summarizes evidence, proposes checks, and
recommends safe operator actions. It does not directly control pumps, valves, dosing, or PLC
setpoints.

## Main entry points

- Python API: `wtdt.agent.operator_agent.diagnose_snapshot(snapshot)`
- Tag API: `wtdt.agent.operator_agent.diagnose_tags(tags)`
- CLI: `wtdt-agent`

## CLI examples

Diagnose a simulated normal snapshot:

```bash
wtdt-agent
```

Diagnose a simulated fault:

```bash
wtdt-agent --fault equipment.dosing_pump_failure --steps 3
```

Diagnose the latest historian state:

```bash
wtdt-agent --latest --historian-path data/historian.sqlite
```

Return JSON for another agent framework:

```bash
wtdt-agent --latest --json
```

## OpenClaw-style linkage

Use OpenClaw as the message router and this project as the water-treatment tool:

```text
OpenClaw chat message
  -> run `wtdt-agent --latest --json`
  -> summarize state, evidence, checks, actions, and safety note
  -> send the result back to the operator
```

Recommended routing:

- "What is wrong with the plant?" -> call `wtdt-agent --latest --json`
- "Explain this alarm" -> call `diagnose_tags` with the alarm snapshot
- "Create daily report" -> combine historian trends with `diagnose_snapshot`

Keep the agent read-only unless a human explicitly approves field action.
