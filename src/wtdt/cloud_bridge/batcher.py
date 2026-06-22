from dataclasses import dataclass, field


@dataclass
class TagBatcher:
    latest_values: dict[str, float] = field(default_factory=dict)
    latest_timestamp_s: float | None = None

    def record(self, tag_name: str, value: float, timestamp_s: float) -> None:
        self.latest_values[tag_name] = value
        if self.latest_timestamp_s is None or timestamp_s > self.latest_timestamp_s:
            self.latest_timestamp_s = timestamp_s

    def flush(self) -> dict[str, object] | None:
        if not self.latest_values:
            return None

        timestamp_s = self.latest_timestamp_s or 0.0
        payload = {
            "ts": int(timestamp_s * 1000),
            "values": dict(self.latest_values),
        }
        self.latest_values.clear()
        self.latest_timestamp_s = None
        return payload
