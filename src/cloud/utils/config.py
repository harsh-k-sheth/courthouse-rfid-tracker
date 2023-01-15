import os
from dataclasses import dataclass


@dataclass
class Config:
    rssi_window_seconds: float = 10.0
    rssi_confidence_threshold: float = 6.0
    locations_table: str = "file_locations"
    movements_table: str = "file_movements"
    readers_table: str = "readers"
    tags_table: str = "tags"
    mqtt_topic_prefix: str = "courthouse/rfid"
    heartbeat_interval_seconds: int = 60
    cors_origin: str = "*"
    stage: str = "dev"
    region: str = "us-east-1"


def get_config():
    return Config(
        rssi_window_seconds=float(os.environ.get("RSSI_WINDOW_SECONDS", "10.0")),
        rssi_confidence_threshold=float(os.environ.get("RSSI_CONFIDENCE_THRESHOLD", "6.0")),
        locations_table=os.environ.get("LOCATIONS_TABLE", "file_locations"),
        movements_table=os.environ.get("MOVEMENTS_TABLE", "file_movements"),
        readers_table=os.environ.get("READERS_TABLE", "readers"),
        tags_table=os.environ.get("TAGS_TABLE", "tags"),
        mqtt_topic_prefix=os.environ.get("MQTT_TOPIC_PREFIX", "courthouse/rfid"),
        heartbeat_interval_seconds=int(os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "60")),
        cors_origin=os.environ.get("CORS_ORIGIN", "*"),
        stage=os.environ.get("STAGE", "dev"),
        region=os.environ.get("AWS_REGION", "us-east-1"),
    )
