"""
Processes RFID tag events from MQTT/IoT Core.
Validates, resolves location via RSSI, updates DynamoDB.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

from ..utils.rssi_resolver import RSSIResolver, RSSIReading, ReaderInfo
from ..utils.db import (
    get_reader_registry, get_tag_registry,
    update_current_location, write_movement_event, get_current_location,
)
from ..utils.config import get_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# persists across warm lambda invocations
_resolver = None
_reader_cache = None
_tag_cache = None
_cache_loaded_at = 0
CACHE_TTL_SECONDS = 300


def _get_resolver():
    global _resolver, _reader_cache, _tag_cache, _cache_loaded_at

    config = get_config()
    now = time.time()

    if _reader_cache is None or (now - _cache_loaded_at) > CACHE_TTL_SECONDS:
        _reader_cache = get_reader_registry()
        _tag_cache = get_tag_registry()
        _cache_loaded_at = now
        logger.info("refreshed caches: %d readers, %d tags", len(_reader_cache), len(_tag_cache))

    if _resolver is None:
        _resolver = RSSIResolver(
            window_seconds=config.rssi_window_seconds,
            confidence_threshold_dbm=config.rssi_confidence_threshold,
            reader_registry=_reader_cache,
        )
    else:
        _resolver.reader_registry = _reader_cache

    return _resolver


def _validate_event(event):
    for f in ["tag_id", "reader_id", "rssi_dbm", "timestamp"]:
        if f not in event:
            logger.warning("missing field: %s", f)
            return None

    event["tag_id"] = event["tag_id"].upper().strip()

    # parse timestamp
    try:
        if isinstance(event["timestamp"], str):
            dt = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            event["timestamp_unix"] = dt.timestamp()
            event["timestamp_iso"] = dt.isoformat()
        elif isinstance(event["timestamp"], (int, float)):
            event["timestamp_unix"] = float(event["timestamp"])
            event["timestamp_iso"] = datetime.fromtimestamp(
                event["timestamp"], tz=timezone.utc).isoformat()
    except (ValueError, OSError):
        return None

    rssi = event["rssi_dbm"]
    if not isinstance(rssi, (int, float)) or rssi < -100 or rssi > 0:
        return None

    return event


def handler(event, context):
    resolver = _get_resolver()
    events = event.get("events", [event]) if "events" in event else [event]

    processed = 0
    skipped = 0
    location_updates = []

    for raw in events:
        validated = _validate_event(raw)
        if validated is None:
            skipped += 1
            continue

        tag_id = validated["tag_id"]
        reader_id = validated["reader_id"]

        if _reader_cache and reader_id not in _reader_cache:
            skipped += 1
            continue

        reading = RSSIReading(
            tag_id=tag_id, reader_id=reader_id,
            rssi_dbm=validated["rssi_dbm"], timestamp=validated["timestamp_unix"],
        )
        resolver.add_reading(reading)

        result = resolver.resolve(tag_id, now=validated["timestamp_unix"])
        if result is None:
            skipped += 1
            continue

        previous = get_current_location(tag_id)
        is_new = previous is None or previous.get("reader_id") != result.reader_id

        tag_info = (_tag_cache or {}).get(tag_id, {})

        update_current_location({
            "tag_id": tag_id,
            "case_number": tag_info.get("case_number", "UNREGISTERED"),
            "case_name": tag_info.get("case_name", "Unknown"),
            "reader_id": result.reader_id,
            "location_label": result.location_label,
            "zone": result.zone,
            "rssi": result.median_rssi,
            "confidence": result.confidence,
            "last_seen": validated["timestamp_iso"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        if is_new:
            if previous:
                write_movement_event({
                    "tag_id": tag_id, "timestamp": validated["timestamp_iso"],
                    "reader_id": previous["reader_id"],
                    "location_label": previous.get("location_label", ""),
                    "zone": previous.get("zone", ""),
                    "event_type": "DEPARTURE", "rssi": previous.get("rssi", 0),
                })
            write_movement_event({
                "tag_id": tag_id, "timestamp": validated["timestamp_iso"],
                "reader_id": result.reader_id,
                "location_label": result.location_label,
                "zone": result.zone,
                "event_type": "ARRIVAL", "rssi": result.median_rssi,
            })
            location_updates.append({
                "tag_id": tag_id, "case_number": tag_info.get("case_number"),
                "from": previous.get("location_label") if previous else None,
                "to": result.location_label, "confidence": result.confidence,
            })

        processed += 1

    return {
        "statusCode": 200,
        "body": {
            "processed": processed, "skipped": skipped,
            "location_updates": location_updates,
        },
    }
