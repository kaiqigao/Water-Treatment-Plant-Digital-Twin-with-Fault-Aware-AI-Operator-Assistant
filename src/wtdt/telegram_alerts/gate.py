from dataclasses import dataclass, field
from time import time
from typing import Callable


@dataclass
class AlarmGate:
    """Convert repeated alarm events into fresh trips with per-code throttling."""

    throttle_s: float = 60.0
    clear_after_s: float = 5.0
    clock: Callable[[], float] = time
    _active_since: dict[str, float] = field(default_factory=dict)
    _last_seen: dict[str, float] = field(default_factory=dict)
    _last_fired: dict[str, float] = field(default_factory=dict)

    def observe(self, code: str) -> bool:
        now = self.clock()
        self.expire()
        self._last_seen[code] = now

        if code in self._active_since:
            return False

        self._active_since[code] = now
        last_fired = self._last_fired.get(code)
        if last_fired is not None and now - last_fired < self.throttle_s:
            return False

        self._last_fired[code] = now
        return True

    def expire(self) -> None:
        now = self.clock()
        stale_codes = [
            code
            for code, last_seen in self._last_seen.items()
            if now - last_seen >= self.clear_after_s
        ]
        for code in stale_codes:
            self._active_since.pop(code, None)
            self._last_seen.pop(code, None)
