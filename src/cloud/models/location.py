from dataclasses import dataclass
from typing import Optional


@dataclass
class FileLocation:
    tag_id: str
    case_number: str
    case_name: str
    reader_id: str
    location_label: str
    zone: str
    rssi: float
    confidence: str
    last_seen: str
    updated_at: str

    def to_dict(self):
        return {
            "tag_id": self.tag_id, "case_number": self.case_number,
            "case_name": self.case_name, "reader_id": self.reader_id,
            "location_label": self.location_label, "zone": self.zone,
            "rssi": self.rssi, "confidence": self.confidence,
            "last_seen": self.last_seen, "updated_at": self.updated_at,
        }


@dataclass
class MovementEvent:
    tag_id: str
    timestamp: str
    reader_id: str
    location_label: str
    zone: str
    event_type: str  # ARRIVAL, DEPARTURE, AMBIGUOUS
    rssi: float
    ttl: Optional[int] = None

    def to_dict(self):
        result = {
            "tag_id": self.tag_id, "timestamp": self.timestamp,
            "reader_id": self.reader_id, "location_label": self.location_label,
            "zone": self.zone, "event_type": self.event_type, "rssi": self.rssi,
        }
        if self.ttl:
            result["ttl"] = self.ttl
        return result
