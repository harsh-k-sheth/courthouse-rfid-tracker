"""Processes heartbeat messages from gateways, tracks reader online/offline."""

import logging
from datetime import datetime, timezone, timedelta
from ..utils.db import get_reader_status, update_reader_status, get_all_reader_statuses

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

HEARTBEAT_INTERVAL = 60
MISSED_THRESHOLD = 3  # mark offline after 3 missed
OFFLINE_TIMEOUT = HEARTBEAT_INTERVAL * MISSED_THRESHOLD


def _check_for_offline_readers():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=OFFLINE_TIMEOUT)
    newly_offline = []

    for reader in get_all_reader_statuses():
        if reader.get("status") != "ONLINE":
            continue
        hb = reader.get("last_heartbeat", "")
        if not hb:
            continue
        try:
            hb_time = datetime.fromisoformat(hb.replace("Z", "+00:00"))
            if hb_time < cutoff:
                update_reader_status(reader["reader_id"], status="OFFLINE", last_heartbeat=hb)
                newly_offline.append(reader)
                logger.warning("reader %s offline (last hb: %s)", reader["reader_id"], hb)
        except ValueError:
            pass

    return newly_offline


def handler(event, context):
    gateway_id = event.get("gateway_id", "unknown")
    readers = event.get("readers", [])
    ts = event.get("timestamp", datetime.now(timezone.utc).isoformat())

    updated = 0
    recovered = 0

    for rd in readers:
        rid = rd.get("reader_id")
        if not rid:
            continue

        prev = get_reader_status(rid)
        was_offline = prev and prev.get("status") == "OFFLINE"

        update_reader_status(
            reader_id=rid, status="ONLINE", last_heartbeat=ts,
            gateway_id=gateway_id,
            metadata={"tags_detected": rd.get("tags_detected_last_minute", 0),
                       "temperature_c": rd.get("temperature_c")},
        )
        updated += 1
        if was_offline:
            recovered += 1

    newly_offline = _check_for_offline_readers()

    return {"statusCode": 200, "body": {
        "gateway_id": gateway_id, "readers_updated": updated,
        "readers_recovered": recovered,
        "readers_newly_offline": len(newly_offline),
    }}
