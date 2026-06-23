import argparse
import json
from pathlib import Path
from typing import Any

from wtdt.agent.fault_detector import detect_basic_faults
from wtdt.agent.operator_agent import OperatorDiagnosis, diagnose_snapshot, diagnose_tags
from wtdt.historian.store import SQLiteHistorian, parse_value
from wtdt.runtime import make_demo_runtime
from wtdt.simulator.process import FaultScenario


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Water treatment operator agent")
    parser.add_argument("--latest", action="store_true", help="diagnose latest historian tags")
    parser.add_argument("--historian-path", type=Path, default=Path("data/historian.sqlite"))
    parser.add_argument("--steps", type=int, default=1, help="simulation steps when not using --latest")
    parser.add_argument("--fault", choices=[scenario.value for scenario in FaultScenario])
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args(argv)

    if args.latest:
        diagnosis = _diagnose_latest(args.historian_path)
    else:
        diagnosis = _diagnose_simulation(args.steps, args.fault)

    if args.json:
        print(json.dumps(_diagnosis_payload(diagnosis), indent=2, sort_keys=True))
    else:
        print(diagnosis.as_text())


def _diagnose_latest(path: Path) -> OperatorDiagnosis:
    if not path.exists():
        return _unknown_historian_diagnosis(path)
    historian = SQLiteHistorian(path)
    try:
        latest = historian.read_latest()
    finally:
        historian.close()
    if not latest:
        return _unknown_historian_diagnosis(path)
    tags = {name: parse_value(value) for name, value in latest.items()}
    detections = detect_basic_faults(tags)
    return diagnose_tags(tags, detections=detections)


def _diagnose_simulation(steps: int, fault: str | None) -> OperatorDiagnosis:
    runtime = make_demo_runtime(fault=fault)
    snapshots = [snapshot for snapshot in runtime.run(steps=max(1, steps))]
    return diagnose_snapshot(snapshots[-1], recent_snapshots=snapshots)


def _diagnosis_payload(diagnosis: OperatorDiagnosis) -> dict[str, Any]:
    return {
        "state": diagnosis.state,
        "severity": diagnosis.severity,
        "summary": diagnosis.summary,
        "evidence": diagnosis.evidence,
        "likely_causes": diagnosis.likely_causes,
        "checks": diagnosis.checks,
        "actions": diagnosis.actions,
        "safety_note": diagnosis.safety_note,
    }


def _unknown_historian_diagnosis(path: Path) -> OperatorDiagnosis:
    return OperatorDiagnosis(
        state="unknown",
        severity="none",
        summary=f"No historian samples are available at {path}.",
        evidence=["The operator agent could not read a latest plant snapshot."],
        likely_causes=["The simulator/dashboard has not written historian data yet."],
        checks=[
            "Start the dashboard or runtime with historian writing enabled.",
            "Confirm the historian path matches the running system configuration.",
        ],
        actions=["Run a live simulation diagnosis or collect historian data before making conclusions."],
        safety_note="Do not infer plant health from missing telemetry.",
    )


if __name__ == "__main__":
    main()
