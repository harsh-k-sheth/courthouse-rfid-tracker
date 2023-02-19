"""
RFID Reader Simulator.

Generates realistic RFID tag detection events for local
development and testing without physical hardware.

Simulates:
  - Multiple files at known locations
  - RSSI values with realistic noise
  - Files being moved between locations
  - Overlapping read zones between adjacent readers
  - Multi-tag stacking (multiple files on same table)
"""

import argparse
import json
import random
import time
import sys
from datetime import datetime, timezone

# Simulated courthouse layout
READERS = {
    "JUDGE-MARTINEZ-BENCH": {"x": 10, "y": 5, "power": 27, "zone": "COURTROOM-1"},
    "CLK-RM3-T1": {"x": 30, "y": 10, "power": 25, "zone": "CLK-RM3-CLUSTER"},
    "CLK-RM3-T2": {"x": 32, "y": 10, "power": 25, "zone": "CLK-RM3-CLUSTER"},
    "ARCHIVE-SHELF-A": {"x": 50, "y": 20, "power": 30, "zone": "ARCHIVE"},
    "ARCHIVE-SHELF-B": {"x": 50, "y": 25, "power": 30, "zone": "ARCHIVE"},
    "COURTROOM2-TABLE": {"x": 10, "y": 30, "power": 28, "zone": "COURTROOM-2"},
    "ATTY-REVIEW-1": {"x": 40, "y": 5, "power": 26, "zone": "ATTY-REVIEW"},
}

# Simulated case files with their RFID tags
FILES = [
    {"tag_id": "4A:7B:2C:9F", "case": "Johnson v. State", "number": "2024-CR-1042"},
    {"tag_id": "3E:8D:1A:5B", "case": "Martinez Estate", "number": "2024-PR-0087"},
    {"tag_id": "7C:2F:9E:4D", "case": "Smith v. Smith", "number": "2024-DR-0234"},
    {"tag_id": "1B:6A:3C:8E", "case": "City v. Thompson", "number": "2024-CR-0891"},
    {"tag_id": "5D:4E:7F:2A", "case": "Williams Trust", "number": "2024-PR-0156"},
    {"tag_id": "9F:1C:6B:3D", "case": "Davis v. County", "number": "2024-CV-0543"},
    {"tag_id": "2A:8E:5C:7B", "case": "Rodriguez Hearing", "number": "2024-CR-1198"},
    {"tag_id": "6D:3F:4A:1E", "case": "Chen v. Global Corp", "number": "2024-CV-0312"},
]

# File placements (which reader each file is near)
FILE_LOCATIONS = {}


def calculate_rssi(file_x, file_y, reader_x, reader_y, reader_power, noise=True):
    """
    Simulate RSSI based on distance between file and reader.

    Uses simplified path loss model:
    RSSI = tx_power - 10 * n * log10(distance) + noise

    Where n is the path loss exponent (2.5 for indoor)
    """
    import math

    distance = math.sqrt((file_x - reader_x) ** 2 + (file_y - reader_y) ** 2)
    if distance < 0.5:
        distance = 0.5  # Minimum distance

    # Path loss model
    n = 2.5  # Indoor path loss exponent
    rssi = reader_power - 10 * n * math.log10(distance) - 40  # -40 offset for UHF

    # Add realistic noise
    if noise:
        rssi += random.gauss(0, 2)  # +/- 2 dBm gaussian noise

    return round(max(-90, min(-20, rssi)), 1)


def simulate_stationary(duration_seconds=60, output="json"):
    """Simulate files sitting at fixed locations."""
    print(f"Simulating stationary files for {duration_seconds}s...")

    # Place files at random readers
    reader_ids = list(READERS.keys())
    for f in FILES:
        reader_id = random.choice(reader_ids)
        reader = READERS[reader_id]
        # File is at the reader location with slight offset
        FILE_LOCATIONS[f["tag_id"]] = {
            "x": reader["x"] + random.uniform(-0.5, 0.5),
            "y": reader["y"] + random.uniform(-0.5, 0.5),
            "reader": reader_id,
        }

    start = time.time()
    event_count = 0

    while time.time() - start < duration_seconds:
        events = []

        for f in FILES:
            loc = FILE_LOCATIONS[f["tag_id"]]

            # Each reader checks if the file is in range
            for reader_id, reader in READERS.items():
                rssi = calculate_rssi(
                    loc["x"], loc["y"],
                    reader["x"], reader["y"],
                    reader["power"],
                )

                # Reader only detects if RSSI is above sensitivity threshold
                if rssi > -70:
                    event = {
                        "tag_id": f["tag_id"],
                        "reader_id": reader_id,
                        "rssi_dbm": rssi,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "gateway_id": "GW-SIM",
                    }
                    events.append(event)
                    event_count += 1

        if events:
            if output == "json":
                batch = {
                    "gateway_id": "GW-SIM",
                    "batch_size": len(events),
                    "events": events,
                }
                print(json.dumps(batch, indent=2))
            else:
                for e in events:
                    print(
                        f"[{e['timestamp']}] {e['tag_id']} -> "
                        f"{e['reader_id']} ({e['rssi_dbm']} dBm)"
                    )

        time.sleep(1)  # 1 read per second per reader

    print(f"\nGenerated {event_count} events in {duration_seconds}s")


def simulate_movement(output="json"):
    """Simulate a file being moved from one location to another."""
    file_info = FILES[0]
    tag_id = file_info["tag_id"]

    print(f"\nSimulating movement of '{file_info['case']}' ({tag_id})")
    print("Route: Clerk Room 3 Table 1 -> (carried) -> Judge Martinez Bench\n")

    start_reader = READERS["CLK-RM3-T1"]
    end_reader = READERS["JUDGE-MARTINEZ-BENCH"]

    # Phase 1: File sitting on clerk desk (5 seconds)
    print("Phase 1: File on Clerk Room 3 Table 1...")
    for i in range(5):
        rssi = calculate_rssi(
            start_reader["x"], start_reader["y"],
            start_reader["x"], start_reader["y"],
            start_reader["power"],
        )
        event = {
            "tag_id": tag_id,
            "reader_id": "CLK-RM3-T1",
            "rssi_dbm": rssi,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        print(f"  [{event['timestamp']}] RSSI: {rssi} dBm (on table)")
        time.sleep(0.5)

    # Phase 2: File picked up and carried (3 seconds, no detection)
    print("\nPhase 2: File picked up, being carried...")
    for i in range(3):
        print(f"  [carrying...] No reader detection (file in transit)")
        time.sleep(1)

    # Phase 3: File placed on judge bench (5 seconds)
    print("\nPhase 3: File placed on Judge Martinez Bench...")
    for i in range(5):
        rssi = calculate_rssi(
            end_reader["x"], end_reader["y"],
            end_reader["x"], end_reader["y"],
            end_reader["power"],
        )
        event = {
            "tag_id": tag_id,
            "reader_id": "JUDGE-MARTINEZ-BENCH",
            "rssi_dbm": rssi,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        print(f"  [{event['timestamp']}] RSSI: {rssi} dBm (on bench)")
        time.sleep(0.5)

    print("\nMovement simulation complete.")


def simulate_overlap_zone(output="json"):
    """Simulate a file in the overlap zone between two close readers."""
    file_info = FILES[2]
    tag_id = file_info["tag_id"]

    t1 = READERS["CLK-RM3-T1"]
    t2 = READERS["CLK-RM3-T2"]

    # File placed exactly between the two tables
    file_x = (t1["x"] + t2["x"]) / 2
    file_y = (t1["y"] + t2["y"]) / 2

    print(f"\nSimulating overlap zone for '{file_info['case']}' ({tag_id})")
    print(f"File at midpoint between CLK-RM3-T1 and CLK-RM3-T2\n")

    for i in range(20):
        rssi_t1 = calculate_rssi(file_x, file_y, t1["x"], t1["y"], t1["power"])
        rssi_t2 = calculate_rssi(file_x, file_y, t2["x"], t2["y"], t2["power"])

        print(
            f"  Read {i+1:2d}: T1={rssi_t1:6.1f} dBm, T2={rssi_t2:6.1f} dBm, "
            f"diff={abs(rssi_t1 - rssi_t2):4.1f} dBm"
        )
        time.sleep(0.5)

    print("\nOverlap simulation complete.")
    print("Note: With noise, RSSI fluctuates. The resolver uses median")
    print("over the window to stabilize, and falls back to zone-level")
    print("reporting when the margin is below the 6 dBm threshold.")


def main():
    parser = argparse.ArgumentParser(description="RFID Reader Simulator")
    parser.add_argument(
        "--mode",
        choices=["stationary", "movement", "overlap"],
        default="stationary",
        help="Simulation mode",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration in seconds (stationary mode)",
    )
    parser.add_argument(
        "--output",
        choices=["json", "text"],
        default="text",
        help="Output format",
    )
    args = parser.parse_args()

    if args.mode == "stationary":
        simulate_stationary(args.duration, args.output)
    elif args.mode == "movement":
        simulate_movement(args.output)
    elif args.mode == "overlap":
        simulate_overlap_zone(args.output)


if __name__ == "__main__":
    main()
