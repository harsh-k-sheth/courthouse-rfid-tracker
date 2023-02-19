"""Seed the reader registry with courthouse reader installations."""

import os
import boto3

DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:8000")
TABLE_NAME = os.environ.get("READERS_TABLE", "readers")

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url=DYNAMODB_ENDPOINT,
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
)

READERS = [
    {
        "reader_id": "JUDGE-MARTINEZ-BENCH",
        "location_label": "Judge Martinez - Bench",
        "zone": "COURTROOM-1",
        "floor": "2",
        "room": "Courtroom 1",
        "power_dbm": 27,
        "status": "ONLINE",
    },
    {
        "reader_id": "CLK-RM3-T1",
        "location_label": "Clerk Room 3 - Table 1",
        "zone": "CLK-RM3-CLUSTER",
        "floor": "1",
        "room": "Clerk Room 3",
        "power_dbm": 25,
        "status": "ONLINE",
    },
    {
        "reader_id": "CLK-RM3-T2",
        "location_label": "Clerk Room 3 - Table 2",
        "zone": "CLK-RM3-CLUSTER",
        "floor": "1",
        "room": "Clerk Room 3",
        "power_dbm": 25,
        "status": "ONLINE",
    },
    {
        "reader_id": "ARCHIVE-SHELF-A",
        "location_label": "Archive Room - Shelf A",
        "zone": "ARCHIVE",
        "floor": "B1",
        "room": "Archive Room",
        "power_dbm": 30,
        "status": "ONLINE",
    },
    {
        "reader_id": "ARCHIVE-SHELF-B",
        "location_label": "Archive Room - Shelf B",
        "zone": "ARCHIVE",
        "floor": "B1",
        "room": "Archive Room",
        "power_dbm": 30,
        "status": "ONLINE",
    },
    {
        "reader_id": "COURTROOM2-TABLE",
        "location_label": "Courtroom 2 - Counsel Table",
        "zone": "COURTROOM-2",
        "floor": "2",
        "room": "Courtroom 2",
        "power_dbm": 28,
        "status": "ONLINE",
    },
    {
        "reader_id": "ATTY-REVIEW-1",
        "location_label": "Attorney Review Room 1",
        "zone": "ATTY-REVIEW",
        "floor": "1",
        "room": "Attorney Review Room",
        "power_dbm": 26,
        "status": "ONLINE",
    },
]


def main():
    table = dynamodb.Table(TABLE_NAME)
    for reader in READERS:
        table.put_item(Item=reader)
        print(f"  Seeded reader: {reader['reader_id']} ({reader['location_label']})")
    print(f"\nSeeded {len(READERS)} readers into {TABLE_NAME}")


if __name__ == "__main__":
    main()
