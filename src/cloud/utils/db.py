"""DynamoDB operations for file tracking."""
"""

import os
import logging
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger(__name__)

# Table name configuration
LOCATIONS_TABLE = os.environ.get("LOCATIONS_TABLE", "file_locations")
MOVEMENTS_TABLE = os.environ.get("MOVEMENTS_TABLE", "file_movements")
READERS_TABLE = os.environ.get("READERS_TABLE", "readers")
TAGS_TABLE = os.environ.get("TAGS_TABLE", "tags")

# DynamoDB resource (reused across Lambda invocations)
_dynamodb = None
MOVEMENT_TTL_DAYS = 90


def _get_dynamodb():
    
    global _dynamodb
    if _dynamodb is None:
        endpoint_url = os.environ.get("DYNAMODB_ENDPOINT")
        if endpoint_url:
            # Local development with DynamoDB Local
            _dynamodb = boto3.resource(
                "dynamodb",
                endpoint_url=endpoint_url,
                region_name="us-east-1",
            )
        else:
            _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def _decimal_to_float(obj):
    
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_float(i) for i in obj]
    return obj


# --- Current Location Operations ---

def get_current_location(tag_id: str) -> Optional[dict]:
    # get current loc
    table = _get_dynamodb().Table(LOCATIONS_TABLE)
    response = table.get_item(Key={"tag_id": tag_id})
    item = response.get("Item")
    return _decimal_to_float(item) if item else None


def update_current_location(record: dict) -> None:
    
    table = _get_dynamodb().Table(LOCATIONS_TABLE)
    # Convert floats to Decimal for DynamoDB
    item = {}
    for k, v in record.items():
        if isinstance(v, float):
            item[k] = Decimal(str(v))
        else:
            item[k] = v
    table.put_item(Item=item)


# TODO: replace scan with GSI query or opensearch for prod scale
def search_files(query: str) -> list[dict]:
    table = _get_dynamodb().Table(LOCATIONS_TABLE)
    query_upper = query.upper()

    response = table.scan(
        FilterExpression=(
            Attr("case_number").contains(query_upper)
            | Attr("case_name").contains(query)
        )
    )
    items = response.get("Items", [])
    return [_decimal_to_float(item) for item in items]


def list_files_by_zone(zone: str) -> list[dict]:
    
    table = _get_dynamodb().Table(LOCATIONS_TABLE)
    response = table.scan(
        FilterExpression=Attr("zone").eq(zone)
    )
    items = response.get("Items", [])
    return [_decimal_to_float(item) for item in items]


# --- Movement History Operations ---

def write_movement_event(record: dict) -> None:
    
    table = _get_dynamodb().Table(MOVEMENTS_TABLE)

    # Add TTL for automatic expiry
    ttl_epoch = int(
        (datetime.now(timezone.utc) + timedelta(days=MOVEMENT_TTL_DAYS)).timestamp()
    )

    item = {**record, "ttl": ttl_epoch}
    for k, v in item.items():
        if isinstance(v, float):
            item[k] = Decimal(str(v))

    table.put_item(Item=item)


def get_movement_history(
    tag_id: str,
    start_time: str,
    end_time: str,
) -> list[dict]:
    table = _get_dynamodb().Table(MOVEMENTS_TABLE)
    response = table.query(
        KeyConditionExpression=(
            Key("tag_id").eq(tag_id)
            & Key("timestamp").between(start_time, end_time)
        ),
        ScanIndexForward=True,  # Chronological order
    )
    items = response.get("Items", [])
    return [_decimal_to_float(item) for item in items]


# --- Reader Operations ---

def get_reader_registry() -> dict[str, dict]:
    
    table = _get_dynamodb().Table(READERS_TABLE)
    response = table.scan()
    items = response.get("Items", [])
    return {
        item["reader_id"]: _decimal_to_float(item)
        for item in items
    }


def get_reader_status(reader_id: str) -> Optional[dict]:
    
    table = _get_dynamodb().Table(READERS_TABLE)
    response = table.get_item(Key={"reader_id": reader_id})
    item = response.get("Item")
    return _decimal_to_float(item) if item else None


def update_reader_status(
    reader_id: str,
    status: str,
    last_heartbeat: str,
    gateway_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    
    table = _get_dynamodb().Table(READERS_TABLE)

    update_expr = "SET #s = :status, last_heartbeat = :hb, updated_at = :now"
    expr_values = {
        ":status": status,
        ":hb": last_heartbeat,
        ":now": datetime.now(timezone.utc).isoformat(),
    }
    expr_names = {"#s": "status"}

    if gateway_id:
        update_expr += ", gateway_id = :gw"
        expr_values[":gw"] = gateway_id

    if metadata:
        update_expr += ", metadata = :meta"
        expr_values[":meta"] = metadata

    table.update_item(
        Key={"reader_id": reader_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


def get_all_reader_statuses() -> list[dict]:
    
    table = _get_dynamodb().Table(READERS_TABLE)
    response = table.scan()
    items = response.get("Items", [])
    return [_decimal_to_float(item) for item in items]


# --- Tag Registry Operations ---

def get_tag_registry() -> dict[str, dict]:
    
    table = _get_dynamodb().Table(TAGS_TABLE)
    response = table.scan()
    items = response.get("Items", [])
    return {
        item["tag_id"]: _decimal_to_float(item)
        for item in items
    }


# --- Analytics Operations ---

def get_idle_files(hours: int = 48) -> list[dict]:
    """Find files that have not moved in the last N hours."""
    table = _get_dynamodb().Table(LOCATIONS_TABLE)
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=hours)
    ).isoformat()

    response = table.scan(
        FilterExpression=Attr("last_seen").lt(cutoff)
    )
    items = response.get("Items", [])
    return [_decimal_to_float(item) for item in items]


def get_zone_traffic(
    zone: str,
    start_time: str,
    end_time: str,
) -> dict:
    table = _get_dynamodb().Table(MOVEMENTS_TABLE)

    # This requires a GSI on zone + timestamp for efficiency.
    # For now, scan with filter (acceptable for moderate data volumes).
    response = table.scan(
        FilterExpression=(
            Attr("zone").eq(zone)
            & Attr("timestamp").between(start_time, end_time)
        )
    )
    items = response.get("Items", [])

    arrivals = [i for i in items if i.get("event_type") == "ARRIVAL"]
    departures = [i for i in items if i.get("event_type") == "DEPARTURE"]
    unique_files = set(i.get("tag_id") for i in items)

    return {
        "zone": zone,
        "start": start_time,
        "end": end_time,
        "total_events": len(items),
        "arrivals": len(arrivals),
        "departures": len(departures),
        "unique_files": len(unique_files),
    }
