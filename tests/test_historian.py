from wtdt.historian.store import SQLiteHistorian, parse_value
from wtdt.runtime import make_demo_runtime


def test_historian_writes_and_reads_snapshot_tags(tmp_path) -> None:
    historian = SQLiteHistorian(tmp_path / "historian.sqlite")
    snapshot = make_demo_runtime().tick()

    historian.write_snapshot(snapshot)
    latest = historian.read_latest()
    level_samples = historian.read_recent("tank_level_pct", limit=5)
    historian.close()

    assert "tank_level_pct" in latest
    assert parse_value(latest["tank_level_pct"]) == snapshot.tags["tank_level_pct"]
    assert level_samples[-1]["tag"] == "tank_level_pct"
