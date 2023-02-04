"""
Deduplicates continuous reads from stationary tags.
File sitting on a table = hundreds of reads/min, only need to
publish the initial detection + periodic refreshes.
"""

import time
from dataclasses import dataclass


@dataclass
class LastPublished:
    tag_id: str
    reader_id: str
    rssi_dbm: float
    timestamp: float


class EventDeduplicator:

    def __init__(self, cooldown_seconds=30.0, rssi_change_threshold=10.0):
        self.cooldown_seconds = cooldown_seconds
        self.rssi_change_threshold = rssi_change_threshold
        self._last_published = {}  # (tag_id, reader_id) -> LastPublished

    def should_publish(self, event):
        tag_id = event["tag_id"]
        reader_id = event["reader_id"]
        rssi = event["rssi_dbm"]
        ts = event.get("timestamp", time.time())
        key = (tag_id, reader_id)

        last = self._last_published.get(key)
        if last is None:
            self._last_published[key] = LastPublished(tag_id, reader_id, rssi, ts)
            return True

        if (ts - last.timestamp) >= self.cooldown_seconds:
            self._last_published[key] = LastPublished(tag_id, reader_id, rssi, ts)
            return True

        if abs(rssi - last.rssi_dbm) >= self.rssi_change_threshold:
            self._last_published[key] = LastPublished(tag_id, reader_id, rssi, ts)
            return True

        return False

    def clear(self):
        self._last_published.clear()

    def get_tracked_pairs(self):
        return len(self._last_published)
