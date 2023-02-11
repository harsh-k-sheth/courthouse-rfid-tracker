

import time
import pytest

from src.cloud.utils.rssi_resolver import (
    RSSIResolver,
    RSSIReading,
    ReaderInfo,
    LocationResult,
)


@pytest.fixture
def reader_registry():
    """Courthouse reader setup for testing."""
    return {
        "CLK-RM3-T1": ReaderInfo(
            reader_id="CLK-RM3-T1",
            location_label="Clerk Room 3 - Table 1",
            zone="CLK-RM3-CLUSTER",
            floor="1",
            room="Clerk Room 3",
        ),
        "CLK-RM3-T2": ReaderInfo(
            reader_id="CLK-RM3-T2",
            location_label="Clerk Room 3 - Table 2",
            zone="CLK-RM3-CLUSTER",
            floor="1",
            room="Clerk Room 3",
        ),
        "JUDGE-BENCH": ReaderInfo(
            reader_id="JUDGE-BENCH",
            location_label="Judge Martinez Bench",
            zone="COURTROOM-1",
            floor="2",
            room="Courtroom 1",
        ),
        "ARCHIVE-A": ReaderInfo(
            reader_id="ARCHIVE-A",
            location_label="Archive Room - Shelf A",
            zone="ARCHIVE",
            floor="B1",
            room="Archive Room",
        ),
    }


@pytest.fixture
def resolver(reader_registry):
    """RSSI resolver with test configuration."""
    return RSSIResolver(
        window_seconds=10.0,
        confidence_threshold_dbm=6.0,
        reader_registry=reader_registry,
    )


class TestSingleReaderDetection:

    def test_single_reader_returns_high_confidence(self, resolver):
        now = time.time()
        tag_id = "AA:BB:CC:DD"

        for i in range(5):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="JUDGE-BENCH",
                rssi_dbm=-35.0,
                timestamp=now + i,
            ))

        result = resolver.resolve(tag_id, now=now + 5)

        assert result is not None
        assert result.reader_id == "JUDGE-BENCH"
        assert result.confidence == "HIGH"
        assert result.location_label == "Judge Martinez Bench"

    def test_no_readings_returns_none(self, resolver):
        result = resolver.resolve("NONEXISTENT")
        assert result is None


class TestOverlappingReadZones:

    def test_clear_winner_above_threshold(self, resolver):
        now = time.time()
        tag_id = "11:22:33:44"

        # Reader A: strong signal (-35 dBm)
        for i in range(10):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="CLK-RM3-T1",
                rssi_dbm=-35.0,
                timestamp=now + i * 0.5,
            ))

        # Reader B: weaker signal (-55 dBm)
        for i in range(10):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="CLK-RM3-T2",
                rssi_dbm=-55.0,
                timestamp=now + i * 0.5,
            ))

        result = resolver.resolve(tag_id, now=now + 5)

        assert result.reader_id == "CLK-RM3-T1"
        assert result.confidence == "HIGH"
        assert result.margin_dbm == 20.0  # 20 dBm > 6 dBm threshold

    def test_ambiguous_below_threshold_same_zone(self, resolver):
        now = time.time()
        tag_id = "55:66:77:88"

        # Both readers at similar RSSI (3 dBm apart < 6 dBm threshold)
        for i in range(10):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="CLK-RM3-T1",
                rssi_dbm=-42.0,
                timestamp=now + i * 0.5,
            ))
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="CLK-RM3-T2",
                rssi_dbm=-45.0,
                timestamp=now + i * 0.5,
            ))

        result = resolver.resolve(tag_id, now=now + 5)

        # Same zone -> zone-level fallback with HIGH confidence
        assert result.confidence == "HIGH"
        assert result.zone == "CLK-RM3-CLUSTER"
        assert "(zone)" in result.location_label

    def test_ambiguous_different_zones_keeps_last_known(self, resolver):
        now = time.time()
        tag_id = "AA:11:BB:22"

        # First establish a known location
        for i in range(10):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="JUDGE-BENCH",
                rssi_dbm=-30.0,
                timestamp=now + i * 0.5,
            ))

        first_result = resolver.resolve(tag_id, now=now + 5)
        assert first_result.reader_id == "JUDGE-BENCH"
        assert first_result.confidence == "HIGH"

        # Now simulate ambiguous readings from two different zones
        later = now + 20  # Outside the first window
        for i in range(10):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="JUDGE-BENCH",
                rssi_dbm=-42.0,
                timestamp=later + i * 0.5,
            ))
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="ARCHIVE-A",
                rssi_dbm=-44.0,
                timestamp=later + i * 0.5,
            ))

        result = resolver.resolve(tag_id, now=later + 5)

        assert result.confidence == "AMBIGUOUS"
        # Should retain last known location
        assert result.reader_id == "JUDGE-BENCH"

    def test_exactly_at_threshold(self, resolver):
        now = time.time()
        tag_id = "EE:FF:00:11"

        for i in range(10):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="CLK-RM3-T1",
                rssi_dbm=-40.0,
                timestamp=now + i * 0.5,
            ))
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="JUDGE-BENCH",
                rssi_dbm=-46.0,  # Exactly 6 dBm difference
                timestamp=now + i * 0.5,
            ))

        result = resolver.resolve(tag_id, now=now + 5)
        assert result.confidence == "HIGH"
        assert result.reader_id == "CLK-RM3-T1"


class TestMedianRSSI:

    def test_median_resists_single_outlier(self, resolver):
        now = time.time()
        tag_id = "CC:DD:EE:FF"

        # 9 readings at -35 dBm (strong, close to reader)
        for i in range(9):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="JUDGE-BENCH",
                rssi_dbm=-35.0,
                timestamp=now + i,
            ))

        # 1 outlier at -70 dBm (person walked past)
        resolver.add_reading(RSSIReading(
            tag_id=tag_id,
            reader_id="JUDGE-BENCH",
            rssi_dbm=-70.0,
            timestamp=now + 9,
        ))

        result = resolver.resolve(tag_id, now=now + 9.5)

        assert result.median_rssi == -35.0  # Median unaffected
        assert result.confidence == "HIGH"

    def test_multiple_outliers_shift_median(self, resolver):
        now = time.time()
        tag_id = "11:AA:22:BB"

        # 4 normal readings
        for i in range(4):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="JUDGE-BENCH",
                rssi_dbm=-35.0,
                timestamp=now + i,
            ))

        # 6 "outlier" readings (now the majority)
        for i in range(6):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="JUDGE-BENCH",
                rssi_dbm=-65.0,
                timestamp=now + 4 + i,
            ))

        result = resolver.resolve(tag_id, now=now + 10)

        # Median should now reflect the weaker signal
        assert result.median_rssi == -65.0


class TestSlidingWindow:

    def test_old_readings_are_pruned(self, resolver):
        now = time.time()
        tag_id = "PP:QQ:RR:SS"

        # Old readings (outside 10-second window)
        for i in range(5):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="CLK-RM3-T1",
                rssi_dbm=-30.0,
                timestamp=now - 20 + i,
            ))

        # Recent readings at a different reader
        for i in range(5):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="JUDGE-BENCH",
                rssi_dbm=-40.0,
                timestamp=now + i,
            ))

        result = resolver.resolve(tag_id, now=now + 5)

        # Should only see the recent reader
        assert result.reader_id == "JUDGE-BENCH"

    def test_file_disappears_returns_last_known(self, resolver):
        now = time.time()
        tag_id = "XX:YY:ZZ:00"

        # File on desk
        for i in range(5):
            resolver.add_reading(RSSIReading(
                tag_id=tag_id,
                reader_id="CLK-RM3-T1",
                rssi_dbm=-35.0,
                timestamp=now + i,
            ))

        result1 = resolver.resolve(tag_id, now=now + 5)
        assert result1.reader_id == "CLK-RM3-T1"

        # File picked up, no new readings for 30 seconds
        result2 = resolver.resolve(tag_id, now=now + 35)

        # Should return last known location
        assert result2.reader_id == "CLK-RM3-T1"


class TestMultipleTagTracking:

    def test_independent_tag_resolution(self, resolver):
        now = time.time()

        # Tag A at desk
        for i in range(5):
            resolver.add_reading(RSSIReading(
                tag_id="TAG-A",
                reader_id="CLK-RM3-T1",
                rssi_dbm=-35.0,
                timestamp=now + i,
            ))

        # Tag B at bench
        for i in range(5):
            resolver.add_reading(RSSIReading(
                tag_id="TAG-B",
                reader_id="JUDGE-BENCH",
                rssi_dbm=-30.0,
                timestamp=now + i,
            ))

        result_a = resolver.resolve("TAG-A", now=now + 5)
        result_b = resolver.resolve("TAG-B", now=now + 5)

        assert result_a.reader_id == "CLK-RM3-T1"
        assert result_b.reader_id == "JUDGE-BENCH"

    def test_stats_tracking(self, resolver):
        now = time.time()

        for tag_num in range(10):
            resolver.add_reading(RSSIReading(
                tag_id=f"TAG-{tag_num:02d}",
                reader_id="CLK-RM3-T1",
                rssi_dbm=-40.0,
                timestamp=now,
            ))

        stats = resolver.get_stats()
        assert stats["tracked_tags"] == 10
        assert stats["registered_readers"] == 4
        assert stats["window_seconds"] == 10.0
        assert stats["confidence_threshold_dbm"] == 6.0
