"""
Integration tests for the gateway-to-cloud event pipeline.

Requires Docker services running (DynamoDB Local).
Tests the full flow: raw RFID event -> event processor -> DynamoDB.
"""

import os
import time
import pytest

# Set test environment
os.environ.setdefault("DYNAMODB_ENDPOINT", "http://localhost:8000")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "local")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "local")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("LOCATIONS_TABLE", "file_locations")
os.environ.setdefault("MOVEMENTS_TABLE", "file_movements")
os.environ.setdefault("READERS_TABLE", "readers")
os.environ.setdefault("TAGS_TABLE", "tags")

from src.cloud.handlers.event_processor import handler
from src.cloud.utils.db import (
    get_current_location,
    get_movement_history,
    update_current_location,
)


@pytest.fixture(autouse=True)
def seed_test_data():
    """Seed reader and tag data before each test."""
    import boto3

    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=os.environ["DYNAMODB_ENDPOINT"],
        region_name="us-east-1",
    )

    # Seed a reader
    readers_table = dynamodb.Table("readers")
    readers_table.put_item(Item={
        "reader_id": "TEST-READER-1",
        "location_label": "Test Room - Desk 1",
        "zone": "TEST-ZONE",
        "floor": "1",
        "room": "Test Room",
        "power_dbm": 25,
        "status": "ONLINE",
    })
    readers_table.put_item(Item={
        "reader_id": "TEST-READER-2",
        "location_label": "Test Room - Desk 2",
        "zone": "TEST-ZONE",
        "floor": "1",
        "room": "Test Room",
        "power_dbm": 25,
        "status": "ONLINE",
    })

    # Seed a tag
    tags_table = dynamodb.Table("tags")
    tags_table.put_item(Item={
        "tag_id": "TEST:AA:BB:CC",
        "case_number": "2024-TEST-001",
        "case_name": "Test Case v. Integration",
    })

    yield

    # Cleanup
    try:
        dynamodb.Table("file_locations").delete_item(Key={"tag_id": "TEST:AA:BB:CC"})
    except Exception:
        pass


class TestEventProcessing:
    """End-to-end event processing tests."""

    def test_single_event_creates_location(self):
        """A single valid event should create a location record."""
        event = {
            "tag_id": "TEST:AA:BB:CC",
            "reader_id": "TEST-READER-1",
            "rssi_dbm": -35.0,
            "timestamp": "2024-11-15T14:32:07Z",
            "gateway_id": "GW-TEST",
        }

        result = handler(event, None)
        assert result["statusCode"] == 200
        assert result["body"]["processed"] == 1

        # Verify location was stored
        location = get_current_location("TEST:AA:BB:CC")
        assert location is not None
        assert location["reader_id"] == "TEST-READER-1"
        assert location["case_number"] == "2024-TEST-001"

    def test_batch_events_processed(self):
        """A batch of events should all be processed."""
        now = time.time()
        event = {
            "events": [
                {
                    "tag_id": "TEST:AA:BB:CC",
                    "reader_id": "TEST-READER-1",
                    "rssi_dbm": -35.0 + i * 0.1,
                    "timestamp": now + i,
                    "gateway_id": "GW-TEST",
                }
                for i in range(5)
            ]
        }

        result = handler(event, None)
        assert result["statusCode"] == 200
        assert result["body"]["processed"] == 5

    def test_unknown_reader_skipped(self):
        """Events from unknown readers should be skipped."""
        event = {
            "tag_id": "TEST:AA:BB:CC",
            "reader_id": "UNKNOWN-READER",
            "rssi_dbm": -35.0,
            "timestamp": "2024-11-15T14:32:07Z",
            "gateway_id": "GW-TEST",
        }

        result = handler(event, None)
        assert result["body"]["skipped"] == 1

    def test_invalid_rssi_rejected(self):
        """Events with out-of-range RSSI should be skipped."""
        event = {
            "tag_id": "TEST:AA:BB:CC",
            "reader_id": "TEST-READER-1",
            "rssi_dbm": 50.0,  # Invalid: positive RSSI
            "timestamp": "2024-11-15T14:32:07Z",
            "gateway_id": "GW-TEST",
        }

        result = handler(event, None)
        assert result["body"]["skipped"] == 1
        assert result["body"]["processed"] == 0
