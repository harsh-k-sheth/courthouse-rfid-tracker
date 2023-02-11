

import time
import pytest

from src.gateway.deduplicator import EventDeduplicator


@pytest.fixture
def dedup():
    return EventDeduplicator(cooldown_seconds=30.0, rssi_change_threshold=10.0)


def _make_event(tag_id="AA:BB:CC:DD", reader_id="R1", rssi=-35.0, ts=None):
    return {
        "tag_id": tag_id,
        "reader_id": reader_id,
        "rssi_dbm": rssi,
        "timestamp": ts or time.time(),
    }


class TestFirstDetection:
    def test_first_read_always_publishes(self, dedup):
        assert dedup.should_publish(_make_event()) is True

    def test_different_tags_both_publish(self, dedup):
        assert dedup.should_publish(_make_event(tag_id="TAG-1")) is True
        assert dedup.should_publish(_make_event(tag_id="TAG-2")) is True

    def test_same_tag_different_readers_both_publish(self, dedup):
        assert dedup.should_publish(_make_event(reader_id="R1")) is True
        assert dedup.should_publish(_make_event(reader_id="R2")) is True


class TestCooldownBehavior:
    def test_duplicate_within_cooldown_suppressed(self, dedup):
        now = time.time()
        assert dedup.should_publish(_make_event(ts=now)) is True
        assert dedup.should_publish(_make_event(ts=now + 5)) is False
        assert dedup.should_publish(_make_event(ts=now + 15)) is False

    def test_publish_after_cooldown_expires(self, dedup):
        now = time.time()
        assert dedup.should_publish(_make_event(ts=now)) is True
        assert dedup.should_publish(_make_event(ts=now + 31)) is True

    def test_cooldown_is_per_tag_reader_pair(self, dedup):
        now = time.time()
        assert dedup.should_publish(_make_event(tag_id="T1", reader_id="R1", ts=now)) is True
        assert dedup.should_publish(_make_event(tag_id="T1", reader_id="R1", ts=now + 5)) is False
        # Same tag, different reader: independent cooldown
        assert dedup.should_publish(_make_event(tag_id="T1", reader_id="R2", ts=now + 5)) is True


class TestRSSIChangeDetection:
    def test_significant_rssi_change_triggers_publish(self, dedup):
        now = time.time()
        assert dedup.should_publish(_make_event(rssi=-35.0, ts=now)) is True
        # 15 dBm change > 10 dBm threshold
        assert dedup.should_publish(_make_event(rssi=-50.0, ts=now + 2)) is True

    def test_small_rssi_change_suppressed(self, dedup):
        now = time.time()
        assert dedup.should_publish(_make_event(rssi=-35.0, ts=now)) is True
        # 5 dBm change < 10 dBm threshold
        assert dedup.should_publish(_make_event(rssi=-40.0, ts=now + 2)) is False


class TestEdgeCases:
    def test_clear_resets_state(self, dedup):
        assert dedup.should_publish(_make_event()) is True
        assert dedup.should_publish(_make_event()) is False
        dedup.clear()
        assert dedup.should_publish(_make_event()) is True

    def test_tracked_pairs_count(self, dedup):
        assert dedup.get_tracked_pairs() == 0
        dedup.should_publish(_make_event(tag_id="T1", reader_id="R1"))
        dedup.should_publish(_make_event(tag_id="T1", reader_id="R2"))
        dedup.should_publish(_make_event(tag_id="T2", reader_id="R1"))
        assert dedup.get_tracked_pairs() == 3
