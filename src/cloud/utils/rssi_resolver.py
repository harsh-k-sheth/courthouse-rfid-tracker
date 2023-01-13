"""
RSSI proximity resolver for overlapping read zones.
Uses sliding window + median to figure out which reader a tag is closest to.
"""

import time
import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional


@dataclass
class RSSIReading:
    tag_id: str
    reader_id: str
    rssi_dbm: float
    timestamp: float


@dataclass
class LocationResult:
    tag_id: str
    reader_id: str
    location_label: str
    zone: str
    median_rssi: float
    confidence: str  # HIGH or AMBIGUOUS
    runner_up_reader: Optional[str] = None
    runner_up_rssi: Optional[float] = None
    margin_dbm: Optional[float] = None


@dataclass
class ReaderInfo:
    reader_id: str
    location_label: str
    zone: str
    floor: str
    room: str
    power_dbm: float = 30.0


class RSSIResolver:
    """
    Figures out which reader (location) a tag is actually at when
    multiple readers pick it up simultaneously.

    Uses median RSSI over a time window instead of mean - median
    handles outliers way better (people walking past, tag orientation, etc).
    """

    def __init__(self, window_seconds=10.0, confidence_threshold_dbm=6.0,
                 max_readings_per_pair=100, reader_registry=None):
        self.window_seconds = window_seconds
        self.confidence_threshold_dbm = confidence_threshold_dbm
        self.max_readings_per_pair = max_readings_per_pair
        self.reader_registry = reader_registry or {}

        # {tag_id: {reader_id: [RSSIReading, ...]}}
        self._readings = defaultdict(lambda: defaultdict(list))
        self._last_known = {}

    def register_reader(self, reader):
        self.reader_registry[reader.reader_id] = reader

    def add_reading(self, reading):
        buffer = self._readings[reading.tag_id][reading.reader_id]
        buffer.append(reading)
        if len(buffer) > self.max_readings_per_pair:
            buffer.pop(0)

    def _prune_window(self, tag_id, now):
        cutoff = now - self.window_seconds
        tag_readings = self._readings[tag_id]

        expired = []
        for reader_id, readings in tag_readings.items():
            tag_readings[reader_id] = [r for r in readings if r.timestamp >= cutoff]
            if not tag_readings[reader_id]:
                expired.append(reader_id)
        for rid in expired:
            del tag_readings[rid]

    def _compute_median_rssi(self, readings):
        # median not mean -- way more resistant to one-off spikes
        return statistics.median(r.rssi_dbm for r in readings)

    def resolve(self, tag_id, now=None):
        if now is None:
            now = time.time()

        self._prune_window(tag_id, now)

        tag_readings = self._readings.get(tag_id)
        if not tag_readings:
            return self._last_known.get(tag_id)

        reader_medians = []
        for reader_id, readings in tag_readings.items():
            if readings:
                med = self._compute_median_rssi(readings)
                reader_medians.append((reader_id, med, len(readings)))

        if not reader_medians:
            return self._last_known.get(tag_id)

        # strongest signal first
        reader_medians.sort(key=lambda x: x[1], reverse=True)

        best_reader_id, best_rssi, _ = reader_medians[0]
        best_info = self.reader_registry.get(best_reader_id)

        # only one reader sees it, easy
        if len(reader_medians) == 1:
            result = LocationResult(
                tag_id=tag_id, reader_id=best_reader_id,
                location_label=best_info.location_label if best_info else best_reader_id,
                zone=best_info.zone if best_info else "unknown",
                median_rssi=best_rssi, confidence="HIGH",
            )
            self._last_known[tag_id] = result
            return result

        runner_reader_id, runner_rssi, _ = reader_medians[1]
        margin = best_rssi - runner_rssi

        if margin >= self.confidence_threshold_dbm:
            result = LocationResult(
                tag_id=tag_id, reader_id=best_reader_id,
                location_label=best_info.location_label if best_info else best_reader_id,
                zone=best_info.zone if best_info else "unknown",
                median_rssi=best_rssi, confidence="HIGH",
                runner_up_reader=runner_reader_id,
                runner_up_rssi=runner_rssi, margin_dbm=margin,
            )
            self._last_known[tag_id] = result
            return result

        # ambiguous -- check if same zone
        runner_info = self.reader_registry.get(runner_reader_id)
        best_zone = best_info.zone if best_info else "unknown"
        runner_zone = runner_info.zone if runner_info else "unknown"

        if best_zone == runner_zone and best_zone != "unknown":
            # same zone, just report at zone level
            result = LocationResult(
                tag_id=tag_id, reader_id=best_reader_id,
                location_label=f"{best_zone} (zone)", zone=best_zone,
                median_rssi=best_rssi, confidence="HIGH",
                runner_up_reader=runner_reader_id,
                runner_up_rssi=runner_rssi, margin_dbm=margin,
            )
            self._last_known[tag_id] = result
            return result

        # different zones, ambiguous -- stick with last known
        last = self._last_known.get(tag_id)
        if last:
            return LocationResult(
                tag_id=tag_id, reader_id=last.reader_id,
                location_label=last.location_label, zone=last.zone,
                median_rssi=best_rssi, confidence="AMBIGUOUS",
                runner_up_reader=runner_reader_id,
                runner_up_rssi=runner_rssi, margin_dbm=margin,
            )

        # no history at all, best guess
        result = LocationResult(
            tag_id=tag_id, reader_id=best_reader_id,
            location_label=best_info.location_label if best_info else best_reader_id,
            zone=best_zone, median_rssi=best_rssi, confidence="AMBIGUOUS",
            runner_up_reader=runner_reader_id,
            runner_up_rssi=runner_rssi, margin_dbm=margin,
        )
        self._last_known[tag_id] = result
        return result

    def get_all_active_tags(self, now=None):
        if now is None:
            now = time.time()
        cutoff = now - self.window_seconds
        active = []
        for tag_id, readers in self._readings.items():
            for readings in readers.values():
                if any(r.timestamp >= cutoff for r in readings):
                    active.append(tag_id)
                    break
        return active

    def clear_tag(self, tag_id):
        self._readings.pop(tag_id, None)
        self._last_known.pop(tag_id, None)

    # TODO: add method to dump full state for debugging overlap issues
    def get_stats(self):
        total = sum(
            len(readings)
            for tag_readers in self._readings.values()
            for readings in tag_readers.values()
        )
        return {
            "tracked_tags": len(self._readings),
            "total_buffered_readings": total,
            "known_locations": len(self._last_known),
            "registered_readers": len(self.reader_registry),
            "window_seconds": self.window_seconds,
            "confidence_threshold_dbm": self.confidence_threshold_dbm,
        }
