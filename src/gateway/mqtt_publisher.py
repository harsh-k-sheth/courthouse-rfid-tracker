"""MQTT client for publishing events to IoT Core."""

import json
import logging
import ssl
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTPublisher:

    def __init__(self, broker_host, broker_port=8883, client_id="gateway",
                 topic_prefix="courthouse/rfid", cert_path=None, key_path=None, ca_path=None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic_prefix = topic_prefix

        self._client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        if cert_path and key_path:
            self._client.tls_set(ca_certs=ca_path, certfile=cert_path,
                                  keyfile=key_path, tls_version=ssl.PROTOCOL_TLSv1_2)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._connected = False

    def _on_connect(self, client, userdata, flags, rc):
        self._connected = (rc == 0)
        if rc == 0:
            logger.info("connected to %s", self.broker_host)
        else:
            logger.error("connect failed: %d", rc)

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc != 0:
            logger.warning("unexpected disconnect rc=%d", rc)

    async def connect(self):
        self._client.connect_async(self.broker_host, self.broker_port)
        self._client.loop_start()

    async def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()

    async def publish(self, topic, payload):
        full_topic = f"{self.topic_prefix}/{topic}"
        result = self._client.publish(full_topic, json.dumps(payload, default=str), qos=1)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise ConnectionError(f"publish failed rc={result.rc}")

    @property
    def connected(self):
        return self._connected
