"""LLRP interface to fixed UHF RFID readers."""
    Interface to a single fixed UHF RFID reader.

    Each reader is mounted at a physical location (desk, shelf,
    bench) and continuously scans for RFID tags in its read range.

    The on_tag_read callback is invoked for every tag detection,
    including the RSSI value used by the gateway's deduplicator
    and the cloud resolver for location determination.
        Args:
            reader_id: Unique identifier for this reader installation.
            host: Reader's IP address or hostname on the local network.
            port: LLRP port (default 5084).
            power_dbm: Transmit power in dBm. Higher power = longer
                range but more overlap with adjacent readers.
                Tuned per room based on physical layout.
            on_tag_read: Callback(tag_id, reader_id, rssi_dbm, timestamp)
        Establish LLRP connection to the reader.

        In production, this uses the sllurp library or a custom
        LLRP client. For this reference implementation, we define
        the interface that wraps the LLRP protocol.
        Run continuous inventory (tag scanning).

        The reader sends a TagReportData notification for every
        tag it detects. Each notification includes:
        - EPC (Electronic Product Code): the tag's unique ID
        - PeakRSSI: signal strength in dBm
        - FirstSeenTimestamp / LastSeenTimestamp
        - AntennaID: which antenna detected the tag
        Process an LLRP TagReportData notification.

        Called by the LLRP client for each tag detection.
        Extracts the EPC and RSSI, formats the tag ID,
        and invokes the callback.
        Get the number of detections in the last minute
        and reset the counter.
        Get reader hardware temperature.
        Available on some reader models via LLRP custom parameters.