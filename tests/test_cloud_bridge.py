import json

import pytest

from wtdt.cloud_bridge.batcher import TagBatcher
from wtdt.cloud_bridge.local_sub import parse_tag_message


def test_parse_tag_message_accepts_reference_payload_shape() -> None:
    payload = json.dumps({"v": 72.4, "t": 1718712345.6}).encode()

    tag_name, value, timestamp_s = parse_tag_message("plant/tags/LT_101", payload)

    assert tag_name == "LT_101"
    assert value == 72.4
    assert timestamp_s == 1718712345.6


def test_parse_tag_message_rejects_non_numeric_value() -> None:
    with pytest.raises(ValueError):
        parse_tag_message("plant/tags/LT_101", b'{"v": "bad"}')


def test_batcher_flushes_latest_values_as_thingsboard_payload() -> None:
    batcher = TagBatcher()

    batcher.record("LT_101", 70.0, 1000.0)
    batcher.record("LT_101", 72.0, 1001.0)
    batcher.record("TT_101", 24.8, 1000.5)

    payload = batcher.flush()

    assert payload == {
        "ts": 1001000,
        "values": {
            "LT_101": 72.0,
            "TT_101": 24.8,
        },
    }
    assert batcher.flush() is None
