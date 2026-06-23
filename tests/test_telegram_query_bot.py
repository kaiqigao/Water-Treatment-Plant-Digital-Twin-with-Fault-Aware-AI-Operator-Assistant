from pathlib import Path

from wtdt.agent.operator_agent import OperatorDiagnosis
from wtdt.telegram_alerts.query_bot import format_diagnosis_reply, reply_to_text


def test_format_diagnosis_reply_includes_agent_sections() -> None:
    diagnosis = OperatorDiagnosis(
        state="alarm",
        severity="high",
        summary="Active abnormal condition detected.",
        evidence=["Dosing flow is zero."],
        checks=["Check pump power."],
        actions=["Switch to standby dosing if available."],
    )

    reply = format_diagnosis_reply(diagnosis)

    assert "[WTDT Operator Agent]" in reply
    assert "state: alarm" in reply
    assert "evidence: Dosing flow is zero." in reply
    assert "check: Check pump power." in reply
    assert "action: Switch to standby dosing if available." in reply


def test_reply_to_text_understands_help() -> None:
    reply = reply_to_text("/help", Path("missing.sqlite"))

    assert "/status" in reply


def test_reply_to_text_understands_chinese_status_question() -> None:
    reply = reply_to_text("现在系统有什么问题？", Path("missing.sqlite"))

    assert "[WTDT Operator Agent]" in reply
    assert "state: unknown" in reply
