"""REST API for the dashboard. Search, location, history, analytics."""

import json
import logging
from datetime import datetime, timezone, timedelta
from ..utils.db import (
    get_current_location, search_files, get_movement_history,
    list_files_by_zone, get_all_reader_statuses, get_idle_files, get_zone_traffic,
)

logger = logging.getLogger(__name__)


def _resp(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "body": json.dumps(body, default=str),
    }


def handler(event, context):
    method = event.get("httpMethod", "GET")
    path = event.get("path", "")
    params = event.get("queryStringParameters") or {}
    path_params = event.get("pathParameters") or {}

    if method == "OPTIONS":
        return _resp(200, {})

    try:
        # search files
        if path == "/files/search":
            q = params.get("q", "").strip()
            if not q:
                return _resp(400, {"error": "q param required"})
            results = search_files(q)
            return _resp(200, {"query": q, "count": len(results), "files": results})

        # current location
        if path.startswith("/files/") and path.endswith("/location"):
            tag_id = path_params.get("tag_id") or path.split("/")[2]
            loc = get_current_location(tag_id)
            if not loc:
                return _resp(404, {"error": f"no data for {tag_id}"})
            return _resp(200, loc)

        # movement history
        if path.startswith("/files/") and path.endswith("/history"):
            tag_id = path_params.get("tag_id") or path.split("/")[2]
            end = params.get("end", datetime.now(timezone.utc).isoformat())
            start = params.get("start", (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat())
            history = get_movement_history(tag_id, start, end)
            return _resp(200, {"tag_id": tag_id, "count": len(history), "movements": history})

        # files in zone
        if path.startswith("/zones/") and path.endswith("/files"):
            zone = path_params.get("zone") or path.split("/")[2]
            files = list_files_by_zone(zone)
            return _resp(200, {"zone": zone, "count": len(files), "files": files})

        # reader health
        if path == "/readers/status":
            statuses = get_all_reader_statuses()
            online = sum(1 for s in statuses if s.get("status") == "ONLINE")
            return _resp(200, {"total": len(statuses), "online": online,
                               "offline": len(statuses) - online, "readers": statuses})

        # idle files
        if path == "/analytics/idle":
            hours = int(params.get("hours", 48))
            files = get_idle_files(hours)
            return _resp(200, {"threshold_hours": hours, "count": len(files), "files": files})

        # zone traffic
        if path == "/analytics/traffic":
            zone = params.get("zone")
            if not zone:
                return _resp(400, {"error": "zone param required"})
            end = params.get("end", datetime.now(timezone.utc).isoformat())
            start = params.get("start", (datetime.now(timezone.utc) - timedelta(days=7)).isoformat())
            return _resp(200, get_zone_traffic(zone, start, end))

        return _resp(404, {"error": f"not found: {path}"})

    except Exception:
        logger.exception("error: %s %s", method, path)
        return _resp(500, {"error": "internal error"})
