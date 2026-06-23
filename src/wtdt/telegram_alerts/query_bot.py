import argparse
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from time import sleep
from typing import Any

from wtdt.agent.operator_agent import OperatorDiagnosis
from wtdt.agent_cli import _diagnose_latest
from wtdt.telegram_alerts.sender import TELEGRAM_API, TelegramSender

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Answer operator questions from Telegram.")
    parser.add_argument("--telegram-token", default=_text_config("TELEGRAM_BOT_TOKEN", ""))
    parser.add_argument("--chat-id", default=_text_config("TELEGRAM_CHAT_ID", ""))
    parser.add_argument(
        "--historian-path",
        type=Path,
        default=Path(_text_config("HISTORIAN_PATH", "data/historian.sqlite")),
    )
    parser.add_argument(
        "--poll-s",
        type=float,
        default=float(_text_config("TELEGRAM_POLL_S", "1.0")),
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=float(_text_config("TELEGRAM_TIMEOUT_S", "15.0")),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=_truthy(_text_config("DRY_RUN", "true")),
    )
    parser.add_argument("--once-text", help="simulate one Telegram message and print the reply")
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
    )

    if args.once_text:
        print(reply_to_text(args.once_text, args.historian_path))
        return

    if not args.telegram_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required for polling Telegram messages")

    print(
        "telegram query bot running: "
        f"historian={args.historian_path} "
        f"allowed_chat={args.chat_id or 'any'} "
        f"dry_run={args.dry_run}"
    )
    poll_telegram(
        token=args.telegram_token,
        allowed_chat_id=args.chat_id,
        historian_path=args.historian_path,
        poll_s=args.poll_s,
        timeout_s=args.timeout_s,
        dry_run=args.dry_run,
    )


def poll_telegram(
    *,
    token: str,
    allowed_chat_id: str,
    historian_path: Path,
    poll_s: float,
    timeout_s: float,
    dry_run: bool,
) -> None:
    offset: int | None = None
    try:
        while True:
            for update in get_updates(token=token, offset=offset, timeout_s=timeout_s):
                offset = int(update["update_id"]) + 1
                _handle_update(
                    token=token,
                    update=update,
                    allowed_chat_id=allowed_chat_id,
                    historian_path=historian_path,
                    dry_run=dry_run,
                    timeout_s=timeout_s,
                )
            sleep(poll_s)
    except KeyboardInterrupt:
        print("telegram query bot stopped")


def get_updates(token: str, offset: int | None, timeout_s: float) -> list[dict[str, Any]]:
    params: dict[str, str | int] = {"timeout": int(timeout_s)}
    if offset is not None:
        params["offset"] = offset
    url = f"{TELEGRAM_API}/bot{token}/getUpdates?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=timeout_s + 5.0) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        log.warning("telegram getUpdates failed: %s", exc)
        return []
    if not body.get("ok"):
        log.warning("telegram getUpdates returned non-ok response")
        return []
    updates = body.get("result", [])
    return updates if isinstance(updates, list) else []


def reply_to_text(text: str, historian_path: Path) -> str:
    if _is_help_text(text):
        return _help_text()
    if _is_status_question(text):
        diagnosis = _diagnose_latest(historian_path)
        return format_diagnosis_reply(diagnosis)
    return (
        "I can answer plant status questions. Try: /status, current status, "
        "现在系统有什么问题？"
    )


def format_diagnosis_reply(diagnosis: OperatorDiagnosis) -> str:
    lines = [
        "[WTDT Operator Agent]",
        f"state: {diagnosis.state}",
        f"severity: {diagnosis.severity}",
        f"summary: {diagnosis.summary}",
    ]
    for item in diagnosis.evidence[:3]:
        lines.append(f"evidence: {item}")
    for item in diagnosis.checks[:3]:
        lines.append(f"check: {item}")
    for item in diagnosis.actions[:3]:
        lines.append(f"action: {item}")
    lines.append(f"safety: {diagnosis.safety_note}")
    return "\n".join(lines)


def _handle_update(
    *,
    token: str,
    update: dict[str, Any],
    allowed_chat_id: str,
    historian_path: Path,
    dry_run: bool,
    timeout_s: float,
) -> None:
    message = update.get("message") or update.get("edited_message") or {}
    if not isinstance(message, dict):
        return
    text = str(message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    if not text or not chat_id:
        return
    if allowed_chat_id and chat_id != allowed_chat_id:
        log.info("ignored message from chat %s", chat_id)
        return

    reply = reply_to_text(text, historian_path)
    TelegramSender(
        token=token,
        chat_id=chat_id,
        dry_run=dry_run,
        timeout_s=timeout_s,
    ).send(reply)


def _is_help_text(text: str) -> bool:
    lowered = text.strip().lower()
    return lowered in {"/start", "/help", "help", "帮助"}


def _is_status_question(text: str) -> bool:
    lowered = text.strip().lower()
    keywords = [
        "/status",
        "status",
        "alarm",
        "problem",
        "wrong",
        "issue",
        "状态",
        "问题",
        "异常",
        "报警",
        "故障",
        "怎么了",
    ]
    return any(keyword in lowered for keyword in keywords)


def _help_text() -> str:
    return (
        "WTDT Operator Agent commands:\n"
        "- /status\n"
        "- 现在系统有什么问题？\n"
        "- any message containing 状态, 问题, 异常, 报警, fault, alarm, or status"
    )


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _text_config(key: str, default: str) -> str:
    value = os.getenv(key)
    if value is not None:
        return value.strip()
    return _dotenv_value(key, default).strip()


def _dotenv_value(key: str, default: str) -> str:
    path = Path(".env")
    if not path.exists():
        return default
    prefix = f"{key}="
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip().strip('"').strip("'")
    return default


if __name__ == "__main__":
    main()
