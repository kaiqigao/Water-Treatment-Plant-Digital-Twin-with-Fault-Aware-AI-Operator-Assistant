# Telegram Alerts

This project includes a Telegram alerter that follows the TUMA206 reference pattern:

```text
simulator -> local Mosquitto -> telegram alerter -> Telegram Bot API -> phone chat
             tuma206/plant1/alarm/event
```

The simulator and PLC do not know Telegram exists. They only publish alarm events to the local
MQTT broker. The alerter is a separate process that subscribes to those events, suppresses repeated
messages while the same alarm is still active, and sends one short Telegram message for a fresh trip.

## Telegram Setup

1. In Telegram, open `@BotFather`.
2. Send `/newbot` and create a bot username ending in `bot`.
3. Copy the HTTP API token into `TELEGRAM_BOT_TOKEN`.
4. Send any message to the new bot.
5. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`.
6. Copy the `chat.id` value into `TELEGRAM_CHAT_ID`.

For a group chat, add the bot to the group, send a message in the group, then refresh `getUpdates`.
Group chat ids are usually negative.

## Configuration

Copy `.env.example` to `.env` and set:

```env
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=123456789
DRY_RUN=true
TELEGRAM_THROTTLE_S=60.0
TELEGRAM_CLEAR_AFTER_S=5.0
```

Keep `DRY_RUN=true` while testing. In dry-run mode, the alerter prints the Telegram message instead
of sending it.

## Local Run

Start Mosquitto and the simulator with MQTT enabled:

```bash
python -m wtdt --mqtt --steps 600 --sleep
```

In another terminal, start the Telegram alerter:

```bash
python -m wtdt.telegram_alerts.main
```

Inject or run a fault scenario so that the simulator publishes to:

```text
tuma206/plant1/alarm/event
```

The alerter sends messages shaped like:

```text
[ALARM] equipment.dosing_pump_failure
severity: high
evidence: Dosing command is 50.0% but flow feedback is 0.00 L/min.
recommendation: Inspect the dosing pump, chemical line, power supply, and valve state.
```

When dry-run output looks correct, set `DRY_RUN=false` and restart the alerter.

## Docker Compose

Run the simulator, MQTT broker, and Telegram alerter:

```bash
docker compose --profile telegram up --build
```

The Compose service reads `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `DRY_RUN`,
`TELEGRAM_THROTTLE_S`, and `TELEGRAM_CLEAR_AFTER_S` from your shell or `.env`.

## Streamlit Fault Buttons

The dashboard also sends Telegram alerts when the Fault Injection buttons create active detections.
This covers:

- `pH Drift`
- `pH Stuck`
- `Dosing Pump`
- `Outlet Valve`
- `pH Shock`
- `Influent Surge`
- `MQTT Link`

For local Streamlit runs, the dashboard reads the Telegram settings from environment variables or
from the local `.env` file.

For Streamlit Cloud, set the same values in the app's Secrets page:

```toml
TELEGRAM_BOT_TOKEN = "123456:ABC..."
TELEGRAM_CHAT_ID = "8669212628"
DRY_RUN = "false"
TELEGRAM_THROTTLE_S = "60.0"
TELEGRAM_CLEAR_AFTER_S = "5.0"
```

Streamlit Cloud does not read the `.env` file from your laptop, so the cloud app will only send
Telegram messages after those secrets are configured in the Streamlit Cloud dashboard and the app is
redeployed.

## Why This Matches the Reference

- Decoupled: the PLC/simulator only publishes local MQTT alarm events.
- Rising-edge style: repeated MQTT events for the same active alarm are suppressed until the alarm
  disappears for `TELEGRAM_CLEAR_AFTER_S`.
- Per-code throttle: a flapping alarm code cannot spam the chat.
- Fail-safe: Telegram send failures are logged; the plant simulation continues running.
