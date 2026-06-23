import os
from html import escape
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from wtdt.historian.store import SQLiteHistorian
from wtdt.runtime import SimulationRuntime
from wtdt.simulator.process import FaultScenario
from wtdt.telegram_alerts.dashboard import alarm_events_from_snapshot
from wtdt.telegram_alerts.gate import AlarmGate
from wtdt.telegram_alerts.main import format_alarm_message
from wtdt.telegram_alerts.sender import TelegramSender


st.set_page_config(page_title="Water Treatment Digital Twin", layout="wide")

RUN_INTERVAL_SECONDS = 1.0
DEFAULT_PH_SETPOINT = 7.0
DEFAULT_TANK_LEVEL_SETPOINT = 60.0
DEFAULT_SPEED_MULTIPLIER = 5.0
MAX_TREND_SAMPLES = 120


def main() -> None:
    _ensure_state()
    _render_page_style()
    _render_controls()
    _render_live_panel()


@st.fragment(run_every=RUN_INTERVAL_SECONDS)
def _render_live_panel() -> None:
    if st.session_state.running:
        _run_cycles(1)

    latest = _latest_snapshot()
    if latest is None:
        _run_cycles(1)
        latest = _latest_snapshot()

    assert latest is not None
    with st.container(border=True):
        _render_section_title("Output Panel", "tank visualization + live data + PID")
        _render_status_strip(latest)
        tank_col, process_col, values_col = st.columns([0.92, 1.3, 1.15], gap="medium")
        with tank_col:
            _render_tank(latest.tags)
        with process_col:
            _render_process_tiles(latest.tags)
        with values_col:
            _render_metrics(latest.tags)

    with st.container(border=True):
        _render_alarms(latest)

    with st.container(border=True):
        _render_trends()


def _ensure_state() -> None:
    if "runtime" not in st.session_state:
        st.session_state.runtime = SimulationRuntime()
    if "snapshots" not in st.session_state:
        st.session_state.snapshots = []
    if "historian" not in st.session_state:
        path = Path(os.environ.get("HISTORIAN_PATH", "data/historian.sqlite"))
        st.session_state.historian = SQLiteHistorian(path)
    if "running" not in st.session_state:
        st.session_state.running = False
    if "ph_setpoint" not in st.session_state:
        st.session_state.ph_setpoint = DEFAULT_PH_SETPOINT
    if "tank_level_setpoint_pct" not in st.session_state:
        st.session_state.tank_level_setpoint_pct = DEFAULT_TANK_LEVEL_SETPOINT
    if "speed_multiplier" not in st.session_state:
        st.session_state.speed_multiplier = DEFAULT_SPEED_MULTIPLIER
    if "telegram_alarm_gate" not in st.session_state:
        st.session_state.telegram_alarm_gate = AlarmGate(
            throttle_s=_float_config("TELEGRAM_THROTTLE_S", 60.0),
            clear_after_s=_float_config("TELEGRAM_CLEAR_AFTER_S", 5.0),
        )
    if "telegram_sender" not in st.session_state:
        st.session_state.telegram_sender = _make_telegram_sender()
    st.session_state.runtime.set_setpoints(
        ph_setpoint=st.session_state.ph_setpoint,
        tank_level_setpoint_pct=st.session_state.tank_level_setpoint_pct,
    )


def _render_page_style() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #f5f7fa;
        }
        .block-container {
            padding-top: 3.2rem;
            padding-bottom: 1.6rem;
            max-width: 1600px;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #ffffff;
            border-color: #d7dce3;
            border-radius: 10px;
            box-shadow: 0 8px 22px rgba(16, 24, 40, 0.04);
        }
        div[data-testid="stButton"] > button {
            min-height: 43px;
            border-radius: 8px;
            border: 1px solid #d7dce3;
            font-weight: 750;
            color: #303642;
            background: #ffffff;
        }
        div[data-testid="stButton"] > button:hover {
            border-color: #94a3b8;
            color: #111827;
        }
        div[data-testid="stSlider"] {
            padding-top: 2px;
        }
        div[data-testid="stSlider"] label {
            font-weight: 760;
            color: #303642;
        }
        .wtdt-section-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            margin: 0 0 12px 0;
        }
        .wtdt-section-title h2 {
            margin: 0;
            font-size: 1.18rem;
            line-height: 1.2;
            color: #111827;
            font-weight: 850;
        }
        .wtdt-section-subtitle {
            color: #6b7280;
            font-weight: 750;
            font-size: .86rem;
            margin-top: 2px;
        }
        .wtdt-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 88px;
            border-radius: 999px;
            padding: 8px 15px;
            font-size: .82rem;
            font-weight: 850;
            color: #fff;
        }
        .wtdt-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(130px, 1fr));
            gap: 10px;
            margin: 0 0 14px 0;
        }
        .wtdt-strip-item {
            border: 1px solid #d7dce3;
            border-radius: 8px;
            padding: 10px 12px;
            background: #ffffff;
        }
        .wtdt-strip-label {
            color: #667085;
            font-size: .76rem;
            margin-bottom: 5px;
        }
        .wtdt-strip-value {
            color: #101828;
            font-size: 1.05rem;
            font-weight: 850;
        }
        .wtdt-card-grid-2,
        .wtdt-card-grid-3 {
            display: grid;
            gap: 10px;
        }
        .wtdt-card-grid-2 {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .wtdt-card-grid-3 {
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }
        .wtdt-card {
            min-height: 70px;
            border: 1px solid #d7dce3;
            border-left: 6px solid var(--accent, #94a3b8);
            border-radius: 8px;
            background: #ffffff;
            padding: 11px 13px;
        }
        .wtdt-card.compact {
            min-height: 66px;
        }
        .wtdt-card-label {
            color: #6b7280;
            font-size: .86rem;
            font-weight: 760;
            margin-bottom: 7px;
        }
        .wtdt-card-value {
            color: #111827;
            font-size: 1.38rem;
            line-height: 1.05;
            font-weight: 900;
            word-break: break-word;
        }
        .wtdt-card.compact .wtdt-card-value {
            font-size: 1.16rem;
        }
        .wtdt-subhead {
            font-size: 1.58rem;
            line-height: 1.15;
            color: #232634;
            font-weight: 900;
            margin: 0 0 10px 0;
        }
        .wtdt-tank-shell {
            height: 355px;
            display: grid;
            place-items: center;
            position: relative;
        }
        .wtdt-tank-caption {
            position: absolute;
            bottom: 2px;
            color: #6b7280;
            font-weight: 760;
            font-size: .84rem;
        }
        .wtdt-alarm-state {
            min-height: 116px;
            border: 1px solid var(--border, #d7dce3);
            background: var(--bg, #ffffff);
            border-radius: 8px;
            padding: 14px 16px;
        }
        .wtdt-alarm-state .state-label {
            color: #6b7280;
            font-weight: 850;
            margin-bottom: 4px;
        }
        .wtdt-alarm-state .state-value {
            color: var(--color, #11845b);
            font-size: 2rem;
            font-weight: 950;
            line-height: 1.05;
            margin-bottom: 10px;
        }
        .wtdt-advisor {
            min-height: 116px;
            border: 1px solid #fed7aa;
            background: #fffaf0;
            border-radius: 8px;
            padding: 14px 16px;
            color: #5f370e;
            font-size: .92rem;
            line-height: 1.32;
        }
        .wtdt-advisor strong {
            display: block;
            color: #7c2d12;
            margin-bottom: 5px;
        }
        @media (max-width: 980px) {
            .wtdt-strip,
            .wtdt-card-grid-3 {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        @media (max-width: 720px) {
            .wtdt-strip,
            .wtdt-card-grid-2,
            .wtdt-card-grid-3 {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _status_pill_html() -> str:
    running = bool(st.session_state.running)
    status_color = "#11845b" if running else "#667085"
    status_text = "RUNNING" if running else "STOPPED"
    return f'<div class="wtdt-pill" style="background:{status_color};">{status_text}</div>'


def _render_section_title(title: str, subtitle: str = "", right_html: str = "") -> None:
    right = right_html or (f'<div class="wtdt-section-subtitle">{escape(subtitle)}</div>' if subtitle else "")
    st.html(
        f"""
        <div class="wtdt-section-title">
          <div>
            <h2>{escape(title)}</h2>
            {f'<div class="wtdt-section-subtitle">{escape(subtitle)}</div>' if subtitle and right_html else ""}
          </div>
          {right}
        </div>
        """
    )


def _render_controls() -> None:
    with st.container(border=True):
        _render_section_title(
            "Control Panel",
            "Water Treatment Plant Digital Twin",
            right_html=_status_pill_html(),
        )

        control_cols = st.columns([1, 1, 1, 1], gap="small")
        control_cols[0].button(
            "Start",
            disabled=st.session_state.running,
            width="stretch",
            on_click=_start_runtime,
        )
        control_cols[1].button(
            "Stop",
            disabled=not st.session_state.running,
            width="stretch",
            on_click=_stop_runtime,
        )
        control_cols[2].button("Reset", width="stretch", on_click=_reset_runtime)
        control_cols[3].button("Clear fault", width="stretch", on_click=_clear_fault)

        setpoint_cols = st.columns([1, 1, 1], gap="medium")
        setpoint_cols[0].slider(
            "pH setpoint",
            min_value=6.5,
            max_value=8.0,
            step=0.05,
            key="ph_setpoint",
            on_change=_apply_setpoints_and_sample,
        )
        setpoint_cols[1].slider(
            "Tank setpoint",
            min_value=35.0,
            max_value=80.0,
            step=1.0,
            format="%.0f%%",
            key="tank_level_setpoint_pct",
            on_change=_apply_setpoints_and_sample,
        )
        setpoint_cols[2].slider(
            "Run speed",
            min_value=1.0,
            max_value=30.0,
            step=1.0,
            format="%.0fx",
            key="speed_multiplier",
        )

        st.caption("Fault Injection")
        fault_scenarios = [
            FaultScenario.SENSOR_PH_DRIFT,
            FaultScenario.SENSOR_PH_STUCK,
            FaultScenario.EQUIPMENT_DOSING_PUMP_FAILURE,
            FaultScenario.EQUIPMENT_OUTLET_VALVE_STUCK,
            FaultScenario.PROCESS_PH_SHOCK,
            FaultScenario.PROCESS_INFLUENT_SURGE,
            FaultScenario.INFRASTRUCTURE_MQTT_DISCONNECTED,
        ]
        fault_cols = st.columns(7, gap="small")
        for index, scenario in enumerate(fault_scenarios):
            fault_cols[index].button(
                _fault_label(scenario),
                width="stretch",
                on_click=_inject_fault,
                args=(scenario,),
            )


def _start_runtime() -> None:
    st.session_state.running = True


def _stop_runtime() -> None:
    st.session_state.running = False


def _reset_runtime() -> None:
    st.session_state.runtime = SimulationRuntime()
    st.session_state.snapshots = []
    st.session_state.running = False
    st.session_state.runtime.set_setpoints(
        ph_setpoint=st.session_state.ph_setpoint,
        tank_level_setpoint_pct=st.session_state.tank_level_setpoint_pct,
    )


def _inject_fault(scenario: FaultScenario) -> None:
    st.session_state.runtime.inject_fault(scenario)
    _run_cycles(1)


def _clear_fault() -> None:
    st.session_state.runtime.clear_fault()
    _run_cycles(1)


def _fault_label(scenario: FaultScenario) -> str:
    labels = {
        FaultScenario.SENSOR_PH_DRIFT: "pH Drift",
        FaultScenario.SENSOR_PH_STUCK: "pH Stuck",
        FaultScenario.EQUIPMENT_DOSING_PUMP_FAILURE: "Dosing Pump",
        FaultScenario.EQUIPMENT_OUTLET_VALVE_STUCK: "Outlet Valve",
        FaultScenario.PROCESS_PH_SHOCK: "pH Shock",
        FaultScenario.PROCESS_INFLUENT_SURGE: "Influent Surge",
        FaultScenario.INFRASTRUCTURE_MQTT_DISCONNECTED: "MQTT Link",
    }
    return labels[scenario]


def _run_cycles(count: int) -> None:
    for _ in range(count):
        snapshot = st.session_state.runtime.tick(seconds=float(st.session_state.speed_multiplier))
        st.session_state.snapshots.append(snapshot)
        st.session_state.historian.write_snapshot(snapshot, source="dashboard")
        _notify_telegram(snapshot)


def _apply_setpoints_and_sample() -> None:
    st.session_state.runtime.set_setpoints(
        ph_setpoint=st.session_state.ph_setpoint,
        tank_level_setpoint_pct=st.session_state.tank_level_setpoint_pct,
    )
    if not st.session_state.running:
        _run_cycles(1)


def _latest_snapshot():
    snapshots = st.session_state.snapshots
    return snapshots[-1] if snapshots else None


def _render_status_strip(snapshot) -> None:
    tags = snapshot.tags
    alarm_color = "#d92d20" if snapshot.alarm_active else "#11845b"
    active_fault = str(tags.get("active_fault") or "none")
    st.html(
        f"""
        <div style="
            display:grid; grid-template-columns:repeat(4, minmax(130px, 1fr));
            gap:10px; margin:4px 0 10px 0;
            font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        ">
          {_strip_item("Cycle", str(snapshot.sequence))}
          {_strip_item("PLC", str(tags["plc_state"]))}
          {_strip_item("Active fault", active_fault)}
          {_strip_item("Alarm", "ACTIVE" if snapshot.alarm_active else "CLEAR", alarm_color)}
        </div>
        """
    )


def _strip_item(label: str, value: str, color: str = "#101828") -> str:
    return f"""
    <div style="border:1px solid #d0d5dd; border-radius:8px; padding:10px 12px; background:#ffffff;">
      <div style="color:#667085; font-size:.76rem; margin-bottom:5px;">{escape(label)}</div>
      <div style="color:{color}; font-size:1.05rem; font-weight:850;">{escape(value)}</div>
    </div>
    """


def _render_process_tiles(tags: dict[str, float | bool | str]) -> None:
    reactor_ph = _bounded_float(tags["reactor_ph"], 0.0, 14.0)
    ph_setpoint = _bounded_float(tags["ph_setpoint"], 0.0, 14.0)
    tank_setpoint = _bounded_float(tags["tank_level_setpoint_pct"], 0.0, 100.0)
    alarm_active = bool(tags["alarm_active"])
    cards = [
        ("pH", f"{reactor_ph:.2f}", _ph_color(reactor_ph)),
        ("pH SP", f"{ph_setpoint:.2f}", "#f59e0b"),
        ("PLC", str(tags["plc_state"]), "#475569"),
        ("Level SP", f"{tank_setpoint:.0f}%", "#f59e0b"),
        ("Influent", f"{float(tags['influent_flow_lpm']):.1f}<br>L/min", "#2563eb"),
        ("Effluent", f"{float(tags['effluent_flow_lpm']):.1f}<br>L/min", "#0f766e"),
        ("Dosing", f"{float(tags['dosing_flow_lpm']):.2f}<br>L/min", "#7c3aed"),
        ("Alarm", "ACTIVE" if alarm_active else "CLEAR", "#d92d20" if alarm_active else "#2f855a"),
    ]
    st.html(_card_grid_html(cards, columns=2))


def _render_metrics(tags: dict[str, float | bool | str]) -> None:
    st.html('<div class="wtdt-subhead">Live Values</div>')
    live_cards = [
        ("Tank level", f"{float(tags['tank_level_pct']):.1f}%", "#94a3b8"),
        ("Reactor pH", f"{float(tags['reactor_ph']):.2f}", "#94a3b8"),
        ("Inlet", "ON" if tags["inlet_pump_cmd"] else "OFF", "#94a3b8"),
        ("Outlet", f"{float(tags['outlet_valve_cmd_pct']):.0f}%", "#94a3b8"),
        ("Dosing cmd", f"{float(tags['dosing_pump_cmd_pct']):.0f}%", "#94a3b8"),
        ("Dose flow", f"{float(tags['dosing_flow_lpm']):.2f} L/min", "#94a3b8"),
    ]
    st.html(_card_grid_html(live_cards, columns=3, compact=True))

    st.html('<div class="wtdt-subhead" style="margin-top:18px;">PID Control</div>')
    pid_cards = [
        ("Level error", f"{float(tags['level_error_pct']):+.1f}%", "#2563eb"),
        ("pH error", f"{float(tags['ph_error']):+.2f}", "#7c3aed"),
        ("Level PID", f"{float(tags['level_pid_output_pct']):+.1f}%", "#2563eb"),
        ("pH PID", f"{float(tags['ph_pid_output_pct']):.1f}%", "#7c3aed"),
    ]
    st.html(_card_grid_html(pid_cards, columns=2, compact=True))


def _card_grid_html(cards: list[tuple[str, str, str]], columns: int, compact: bool = False) -> str:
    grid_class = "wtdt-card-grid-3" if columns == 3 else "wtdt-card-grid-2"
    card_class = "wtdt-card compact" if compact else "wtdt-card"
    card_html = "\n".join(
        f"""
        <div class="{card_class}" style="--accent:{accent};">
          <div class="wtdt-card-label">{escape(label)}</div>
          <div class="wtdt-card-value">{value}</div>
        </div>
        """
        for label, value, accent in cards
    )
    return f'<div class="{grid_class}">{card_html}</div>'


def _render_tank(tags: dict[str, float | bool | str]) -> None:
    level = _bounded_float(tags["tank_level_pct"], 0.0, 100.0)
    alarm_active = bool(tags["alarm_active"])
    tank_setpoint = _bounded_float(tags["tank_level_setpoint_pct"], 0.0, 100.0)
    alarm_ring = "#d92d20" if alarm_active else "#2f855a"
    fill_top = 100.0 - level
    setpoint_top = 100.0 - tank_setpoint

    st.html(
        f"""
        <div class="wtdt-tank-shell">
          <div style="
            width:260px; height:300px; position:relative;
            border:7px solid {alarm_ring};
            border-radius:18px 18px 28px 28px; overflow:hidden;
            background:linear-gradient(180deg, #f8fbff 0%, #eef4f8 100%);
            box-shadow: inset 0 0 0 2px rgba(255,255,255,.8), 0 15px 28px rgba(30,54,71,.14);
          ">
            <div style="
              position:absolute; left:0; right:0; bottom:0; top:{fill_top:.1f}%;
              background:linear-gradient(180deg, #62b8e8 0%, #2f77b9 100%);
              transition:top .25s ease;
            "></div>
            <div style="
              position:absolute; left:0; right:0; top:{fill_top:.1f}%;
              height:10px; transform:translateY(-5px);
              background:rgba(255,255,255,.62);
            "></div>
            <div style="
              position:absolute; left:0; right:0; top:{setpoint_top:.1f}%;
              height:4px; background:#f59e0b;
              box-shadow:0 0 0 1px rgba(255,255,255,.9);
            "></div>
            <div style="
              position:absolute; inset:0; display:grid; place-items:center;
              color:#12243b; font-weight:950; font-size:40px;
              text-shadow:0 1px 0 rgba(255,255,255,.8);
            ">{level:.1f}%</div>
          </div>
          <div style="
            position:absolute; left:calc(50% - 150px); right:calc(50% - 150px); bottom:28px;
            height:18px; border-radius:50%; background:#607d8b; opacity:.26;
          "></div>
          <div class="wtdt-tank-caption">orange line = tank setpoint {tank_setpoint:.0f}%</div>
        </div>
        """
    )


def _tank_stat(label: str, value: str, color: str) -> str:
    return f"""
    <div style="
      min-height:74px; border:1px solid #d0d5dd; border-left:6px solid {color};
      border-radius:8px; padding:10px 12px; background:#ffffff;
    ">
      <div style="font-size:13px; color:#667085; margin-bottom:6px;">{escape(label)}</div>
      <div style="font-size:22px; font-weight:760; color:#101828; line-height:1.1;">{escape(value)}</div>
    </div>
    """


def _bounded_float(value: float | bool | str, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


def _ph_color(reactor_ph: float) -> str:
    if reactor_ph < 6.2 or reactor_ph > 7.8:
        return "#d92d20"
    if reactor_ph < 6.8 or reactor_ph > 7.3:
        return "#dc6803"
    return "#11845b"


def _render_trends() -> None:
    _render_section_title("Trends", "reset clears chart history and redraws from cycle 1")
    history = _history_frame(
        [
            "tank_level_pct",
            "tank_level_setpoint_pct",
            "reactor_ph",
            "ph_setpoint",
            "dosing_flow_lpm",
            "ph_pid_output_pct",
            "level_pid_output_pct",
        ]
    )
    if history.empty:
        st.info("No trend samples yet.")
        return

    left, right = st.columns(2, gap="medium")
    level_ph = history[
        history["tag"].isin(["tank_level_pct", "tank_level_setpoint_pct", "reactor_ph", "ph_setpoint"])
    ]
    dosing = history[history["tag"].isin(["dosing_flow_lpm", "ph_pid_output_pct", "level_pid_output_pct"])]
    with left:
        _render_trend_chart(
            level_ph,
            ["ph_setpoint", "reactor_ph", "tank_level_pct", "tank_level_setpoint_pct"],
            ["#2563eb", "#93c5fd", "#ef4444", "#fca5a5"],
        )
    with right:
        _render_trend_chart(
            dosing,
            ["dosing_flow_lpm", "level_pid_output_pct", "ph_pid_output_pct"],
            ["#2563eb", "#93c5fd", "#ef4444"],
        )


def _render_trend_chart(frame: pd.DataFrame, domain: list[str], colors: list[str]) -> None:
    chart = (
        alt.Chart(frame)
        .mark_line(strokeWidth=3)
        .encode(
            x=alt.X("sample:Q", title="sample"),
            y=alt.Y("value:Q", title="value"),
            color=alt.Color(
                "tag:N",
                scale=alt.Scale(domain=domain, range=colors),
                legend=alt.Legend(title="tag", orient="bottom", columns=2),
            ),
            order="sample:Q",
        )
        .properties(height=300)
    )
    st.altair_chart(chart, width="stretch")


def _history_frame(tags: list[str]) -> pd.DataFrame:
    rows = []
    snapshots = st.session_state.snapshots[-MAX_TREND_SAMPLES:]
    for index, snapshot in enumerate(snapshots):
        for tag in tags:
            value = snapshot.tags.get(tag)
            if isinstance(value, (float, int)):
                rows.append({"sample": index, "tag": tag, "value": float(value)})
    return pd.DataFrame(rows)


def _render_alarms(snapshot) -> None:
    _render_section_title("Alarm System", "current status + evidence + assistant action")
    state_col, table_col, advice_col = st.columns([0.85, 2.25, 1.1], gap="small")
    state_text = "ACTIVE" if snapshot.alarm_active else "CLEAR"
    state_color = "#d92d20" if snapshot.alarm_active else "#2f855a"
    state_bg = "#fff7f6" if snapshot.alarm_active else "#f0fdf4"
    state_border = "#f2b8b5" if snapshot.alarm_active else "#bbf7d0"
    severity = snapshot.detections[0].severity if snapshot.detections else "none"
    with state_col:
        st.html(
            f"""
            <div class="wtdt-alarm-state" style="--color:{state_color}; --bg:{state_bg}; --border:{state_border};">
              <div class="state-label">Alarm state</div>
              <div class="state-value">{state_text}</div>
              <div style="font-weight:850;color:#111827;">Severity: {escape(severity)}</div>
            </div>
            """
        )

    if not snapshot.detections:
        with table_col:
            st.dataframe(
                pd.DataFrame(
                    [{"severity": "none", "code": "clear", "evidence": "No active alarms detected."}]
                ),
                hide_index=True,
                width="stretch",
                height=116,
            )
        with advice_col:
            st.html(
                """
                <div class="wtdt-advisor">
                  <strong>Assistant recommendation</strong>
                  Continue monitoring the plant. No operator intervention is required.
                </div>
                """
            )
        return

    alarm_rows = [
        {
            "severity": detection.severity,
            "code": detection.code,
            "evidence": " ".join(detection.evidence),
        }
        for detection, recommendation in zip(
            snapshot.detections,
            snapshot.recommendations,
            strict=True,
        )
    ]
    with table_col:
        st.dataframe(pd.DataFrame(alarm_rows), hide_index=True, width="stretch", height=116)
    recommendations = "<br>".join(escape(recommendation) for recommendation in snapshot.recommendations)
    with advice_col:
        st.html(
            f"""
            <div class="wtdt-advisor">
              <strong>Assistant recommendation</strong>
              {recommendations}
            </div>
            """
        )


def _notify_telegram(snapshot) -> None:
    gate = st.session_state.telegram_alarm_gate
    sender = st.session_state.telegram_sender
    gate.expire()
    if sender is None:
        return
    for event in alarm_events_from_snapshot(snapshot):
        if gate.observe(event.code):
            sender.send(format_alarm_message(event))


def _make_telegram_sender() -> TelegramSender | None:
    token = _text_config("TELEGRAM_BOT_TOKEN", "")
    chat_id = _text_config("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id or "paste_your" in token or "paste_your" in chat_id:
        return None
    return TelegramSender(
        token=token,
        chat_id=chat_id,
        dry_run=_bool_config("DRY_RUN", False),
    )


def _text_config(key: str, default: str) -> str:
    value = _streamlit_secret(key)
    if value is not None:
        return str(value).strip()
    value = os.getenv(key)
    if value is not None:
        return value.strip()
    return _dotenv_value(key, default).strip()


def _bool_config(key: str, default: bool) -> bool:
    value = _text_config(key, "")
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _float_config(key: str, default: float) -> float:
    value = _text_config(key, "")
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _streamlit_secret(key: str) -> Any | None:
    try:
        return st.secrets.get(key)
    except Exception:
        return None


def _dotenv_value(key: str, default: str) -> str:
    path = Path(".env")
    if not path.exists():
        return default
    prefix = f"{key}="
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(prefix):
            return line.removeprefix(prefix)
    return default


if __name__ == "__main__":
    main()
