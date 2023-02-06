"""Edge gateway - aggregates RFID reads and publishes to cloud via MQTT."""
  - Send periodic heartbeats for reader health monitoring
    Main gateway process that orchestrates reader communication,
    deduplication, and cloud publishing.
        Callback invoked by ReaderInterface when a tag is detected.

        Applies deduplication before buffering the event.
        A file sitting on a table will be read continuously
        (multiple times per second). We only want to record it
        once and then again if the RSSI changes significantly
        (indicating the file may have been picked up or moved).
