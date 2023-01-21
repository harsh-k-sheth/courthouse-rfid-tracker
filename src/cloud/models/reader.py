from dataclasses import dataclass
from typing import Optional


@dataclass
class Reader:
    reader_id: str
    location_label: str
    zone: str
    floor: str
    room: str
    power_dbm: float = 30.0
    status: str = "ONLINE"
    last_heartbeat: Optional[str] = None
    gateway_id: Optional[str] = None

    def to_dict(self):
        d = {
            "reader_id": self.reader_id, "location_label": self.location_label,
            "zone": self.zone, "floor": self.floor, "room": self.room,
            "power_dbm": self.power_dbm, "status": self.status,
        }
        if self.last_heartbeat:
            d["last_heartbeat"] = self.last_heartbeat
        if self.gateway_id:
            d["gateway_id"] = self.gateway_id
        return d
