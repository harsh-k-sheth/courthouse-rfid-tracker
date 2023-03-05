# Courthouse RFID File Tracking System

Real-time location tracking for physical court case files using passive UHF RFID tags, IoT edge gateways, and cloud-native event processing.

## Problem

In courthouses, physical case files move between judges' chambers, clerk offices, courtrooms, archive rooms, and attorney review tables. A single file might pass through 10-15 hands in a day. When a judge needs a file and it is not where it should be, someone has to physically search for it. Files go missing for hours or even days, causing hearing delays, missed deadlines, and operational chaos.

Existing tracking methods (paper sign-out sheets, manual logs) depend on human compliance, which is inconsistent at best.

## Solution

Every case file gets a passive UHF RFID tag (thin, sticker-like, no battery required). Fixed RFID readers are installed at every workstation, desk, and shelf throughout the courthouse. When a file is placed on a surface, the nearest reader detects the tag and publishes a location event to the cloud backend. Staff can look up any file's current location and full movement history through a web dashboard.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        COURTHOUSE FLOOR                             │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Reader A │  │ Reader B │  │ Reader C │  │ Reader D │  ...       │
│  │ (Desk 1) │  │ (Desk 2) │  │ (Bench)  │  │ (Shelf)  │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       └──────┬───────┴──────┬──────┘             │                  │
│              │              │                    │                  │
│         ┌────▼──────────────▼────────────────────▼───┐             │
│         │          EDGE GATEWAY (Raspberry Pi)        │             │
│         │  - Batch reads (reduce network chatter)     │             │
│         │  - Deduplicate continuous detections         │             │
│         │  - RSSI-based location resolution            │             │
│         │  - MQTT publish to cloud                     │             │
│         └──────────────────┬─────────────────────────┘             │
└────────────────────────────┼────────────────────────────────────────┘
                             │ MQTT over TLS
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         CLOUD BACKEND                               │
│                                                                     │
│  ┌───────────────┐    ┌──────────────────┐    ┌──────────────────┐ │
│  │  IoT Core /   │───▶│  Lambda / Azure   │───▶│  DynamoDB /      │ │
│  │  IoT Hub      │    │  Function         │    │  Cosmos DB       │ │
│  │  (MQTT Broker)│    │  (Event Processor)│    │  (Location Store)│ │
│  └───────────────┘    └──────────────────┘    └──────────────────┘ │
│                              │                        │             │
│                              ▼                        ▼             │
│                       ┌──────────────┐    ┌──────────────────────┐ │
│                       │  CloudWatch  │    │  API Gateway +       │ │
│                       │  (Alerts)    │    │  Lambda (REST API)   │ │
│                       └──────────────┘    └──────────┬───────────┘ │
└──────────────────────────────────────────────────────┼──────────────┘
                                                       │
                                                       ▼
                                              ┌──────────────────┐
                                              │   Web Dashboard  │
                                              │   (React + Maps) │
                                              └──────────────────┘
```

## Key Technical Challenge: Overlapping Read Zones

RFID readers do not have precise boundaries. A UHF reader's range extends 1-3 meters depending on power, antenna design, tag orientation, and environment. When two desks are side by side, a file on Desk A might be detected by both Reader A and Reader B simultaneously.

### Solution: RSSI-Based Proximity Scoring with Sliding Window

1. **Collect RSSI (signal strength) readings** over a configurable time window (default: 10 seconds)
2. **Compute the median RSSI** per tag-reader pair (median resists outliers better than mean)
3. **Compare across all readers** that detected the tag
4. **Assign location** to the reader with the highest median RSSI
5. **Apply confidence threshold**: the winning reader must be at least 6 dBm stronger than the runner-up, otherwise report "ambiguous" and retain the previous known location
6. **Zone-based fallback**: for tables too close together, group into a single logical zone

The 6 dBm threshold was determined experimentally through controlled placement testing.

```
Reader A (RSSI: -35 dBm)  ◄── File is HERE (stronger signal = closer)
Reader B (RSSI: -55 dBm)      Difference: 20 dBm > 6 dBm threshold ✓

Reader A (RSSI: -42 dBm)      Difference: 3 dBm < 6 dBm threshold ✗
Reader B (RSSI: -45 dBm)      Result: AMBIGUOUS → keep previous location
```

## Project Structure

```
courthouse-rfid-tracker/
├── src/
│   ├── cloud/                    # Cloud backend (Lambda / Azure Functions)
│   │   ├── handlers/
│   │   │   ├── event_processor.py       # Core MQTT event handler
│   │   │   ├── location_api.py          # REST API for dashboard queries
│   │   │   └── health_monitor.py        # Reader health check handler
│   │   ├── models/
│   │   │   ├── location.py              # Location data models
│   │   │   └── reader.py                # Reader registry models
│   │   └── utils/
│   │       ├── rssi_resolver.py         # RSSI sliding window + proximity scoring
│   │       ├── db.py                    # DynamoDB/Cosmos DB operations
│   │       └── config.py               # Environment configuration
│   │
│   ├── gateway/                  # Edge gateway (Raspberry Pi / Linux box)
│   │   ├── gateway.py                   # Main gateway process
│   │   ├── reader_interface.py          # RFID reader communication (LLRP)
│   │   ├── deduplicator.py              # Event deduplication logic
│   │   ├── mqtt_publisher.py            # MQTT client for cloud publish
│   │   └── config.yaml                  # Gateway configuration
│   │
│   └── dashboard/                # Web dashboard (React)
│       ├── src/
│       │   ├── App.jsx
│       │   ├── components/
│       │   │   ├── FileSearch.jsx        # Search by case number/name
│       │   │   ├── FloorMap.jsx          # SVG floor map with file locations
│       │   │   ├── MovementTimeline.jsx  # File movement history
│       │   │   ├── ReaderStatus.jsx      # Reader health dashboard
│       │   │   └── LiveFeed.jsx          # Real-time location updates
│       │   └── hooks/
│       │       └── useWebSocket.js       # WebSocket for live updates
│       ├── package.json
│       └── index.html
│
├── infrastructure/
│   ├── terraform/                # Infrastructure as Code
│   │   ├── modules/
│   │   │   ├── iot/                     # IoT Core / IoT Hub
│   │   │   ├── compute/                 # Lambda / Azure Functions
│   │   │   ├── database/                # DynamoDB / Cosmos DB
│   │   │   └── networking/              # VPC, API Gateway
│   │   └── environments/
│   │       ├── dev/
│   │       └── prod/
│   └── docker/
│       ├── Dockerfile.gateway           # Gateway container image
│       └── docker-compose.yml           # Local development stack
│
├── tests/
│   ├── unit/
│   │   ├── test_rssi_resolver.py        # RSSI algorithm tests
│   │   ├── test_deduplicator.py         # Dedup logic tests
│   │   └── test_event_processor.py      # Event handler tests
│   ├── integration/
│   │   ├── test_gateway_to_cloud.py     # End-to-end event flow
│   │   └── test_api_queries.py          # REST API tests
│   └── load/
│       └── artillery_config.yml         # Load testing config
│
├── scripts/
│   ├── simulate_readers.py              # Simulate RFID reader events
│   ├── seed_readers.py                  # Seed reader registry
│   ├── seed_files.py                    # Seed file/tag mappings
│   └── run_placement_test.py            # Controlled placement test runner
│
├── docs/
│   ├── diagrams/
│   │   ├── architecture.mermaid         # System architecture
│   │   ├── event_flow.mermaid           # Event processing pipeline
│   │   ├── rssi_resolution.mermaid      # RSSI algorithm flow
│   │   └── database_schema.mermaid      # Data model
│   └── DEPLOYMENT.md                    # Deployment guide
│
├── .github/
│   └── workflows/
│       ├── ci.yml                       # Test + lint on PR
│       └── deploy.yml                   # Deploy to AWS/Azure
│
├── .env.example
├── requirements.txt
├── pyproject.toml
└── LICENSE
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| RFID Hardware | Passive UHF tags, Impinj/Zebra fixed readers |
| Edge Gateway | Python, LLRP protocol, MQTT (Paho) |
| Message Broker | AWS IoT Core / Azure IoT Hub |
| Event Processing | AWS Lambda / Azure Functions (Python) |
| Database | DynamoDB / Cosmos DB (key-value + time-series) |
| REST API | API Gateway + Lambda |
| Dashboard | React, WebSocket, SVG floor maps |
| Infrastructure | Terraform, Docker |
| CI/CD | GitHub Actions |
| Monitoring | CloudWatch / Azure Monitor |

## Database Schema

### Current Location Table (`file_locations`)

| Attribute | Type | Description |
|-----------|------|-------------|
| `tag_id` (PK) | String | RFID tag unique identifier |
| `case_number` | String | Court case file number (GSI) |
| `case_name` | String | Case display name |
| `reader_id` | String | Current reader/location ID |
| `location_label` | String | Human-readable location |
| `zone` | String | Logical zone grouping |
| `rssi` | Number | Signal strength at detection |
| `confidence` | String | HIGH / AMBIGUOUS |
| `last_seen` | String (ISO) | Timestamp of last detection |
| `updated_at` | String (ISO) | Last record update |

### Movement History Table (`file_movements`)

| Attribute | Type | Description |
|-----------|------|-------------|
| `tag_id` (PK) | String | RFID tag identifier |
| `timestamp` (SK) | String (ISO) | Event timestamp |
| `reader_id` | String | Reader that detected the tag |
| `location_label` | String | Human-readable location |
| `zone` | String | Logical zone |
| `event_type` | String | ARRIVAL / DEPARTURE / AMBIGUOUS |
| `rssi` | Number | Signal strength |
| `ttl` | Number | Auto-expiry (epoch, 90 days) |

### Reader Registry Table (`readers`)

| Attribute | Type | Description |
|-----------|------|-------------|
| `reader_id` (PK) | String | Unique reader identifier |
| `location_label` | String | Where this reader is installed |
| `zone` | String | Logical zone grouping |
| `floor` | String | Building floor |
| `room` | String | Room identifier |
| `power_dbm` | Number | Configured transmit power |
| `status` | String | ONLINE / OFFLINE |
| `last_heartbeat` | String (ISO) | Last health check |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- AWS CLI or Azure CLI (for cloud deployment)
- Terraform 1.5+

### Local Development

```bash
# Clone the repo
git clone https://github.com/harshksheth/courthouse-rfid-tracker.git
cd courthouse-rfid-tracker

# Install Python dependencies
pip install -r requirements.txt

# Start local infrastructure (DynamoDB Local, MQTT broker)
docker-compose -f infrastructure/docker/docker-compose.yml up -d

# Seed test data
python scripts/seed_readers.py
python scripts/seed_files.py

# Run the event simulator
python scripts/simulate_readers.py

# Start the dashboard
cd src/dashboard
npm install
npm run dev
```

### Running Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires Docker services running)
pytest tests/integration/ -v

# RSSI algorithm tests with coverage
pytest tests/unit/test_rssi_resolver.py -v --cov=src/cloud/utils/rssi_resolver
```

### Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full AWS and Azure deployment instructions.

```bash
# AWS deployment
cd infrastructure/terraform/environments/dev
terraform init
terraform plan
terraform apply

# Deploy Lambda functions
cd ../../../../
./scripts/deploy_lambda.sh dev
```

## Testing

Tested with controlled placement, walking paths, multi-tag stacking, and power tuning at different levels per room.

## License

MIT License. See [LICENSE](LICENSE) for details.
