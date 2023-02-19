"""Seed the tag registry with case file RFID tag mappings."""

import os
from datetime import datetime, timezone

import boto3

DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:8000")
TABLE_NAME = os.environ.get("TAGS_TABLE", "tags")

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url=DYNAMODB_ENDPOINT,
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
)

FILES = [
    {
        "tag_id": "4A:7B:2C:9F",
        "case_number": "2024-CR-1042",
        "case_name": "Johnson v. State",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "registered_by": "Clerk Thompson",
    },
    {
        "tag_id": "3E:8D:1A:5B",
        "case_number": "2024-PR-0087",
        "case_name": "Martinez Estate",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "registered_by": "Clerk Thompson",
    },
    {
        "tag_id": "7C:2F:9E:4D",
        "case_number": "2024-DR-0234",
        "case_name": "Smith v. Smith",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "registered_by": "Clerk Davis",
    },
    {
        "tag_id": "1B:6A:3C:8E",
        "case_number": "2024-CR-0891",
        "case_name": "City v. Thompson",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "registered_by": "Clerk Davis",
    },
    {
        "tag_id": "5D:4E:7F:2A",
        "case_number": "2024-PR-0156",
        "case_name": "Williams Trust",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "registered_by": "Clerk Martinez",
    },
    {
        "tag_id": "9F:1C:6B:3D",
        "case_number": "2024-CV-0543",
        "case_name": "Davis v. County",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "registered_by": "Clerk Martinez",
    },
    {
        "tag_id": "2A:8E:5C:7B",
        "case_number": "2024-CR-1198",
        "case_name": "Rodriguez Hearing",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "registered_by": "Clerk Thompson",
    },
    {
        "tag_id": "6D:3F:4A:1E",
        "case_number": "2024-CV-0312",
        "case_name": "Chen v. Global Corp",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "registered_by": "Clerk Davis",
    },
]


def main():
    table = dynamodb.Table(TABLE_NAME)
    for f in FILES:
        table.put_item(Item=f)
        print(f"  Seeded tag: {f['tag_id']} -> {f['case_number']} ({f['case_name']})")
    print(f"\nSeeded {len(FILES)} file tags into {TABLE_NAME}")


if __name__ == "__main__":
    main()
