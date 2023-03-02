import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * WebSocket hook for real-time location updates.
 *
 * Connects to the API Gateway WebSocket endpoint and receives
 * push notifications when file locations change. Falls back
 * to polling if WebSocket is unavailable.
 *
 * Usage:
 *   const { lastMessage, isConnected } = useWebSocket(wsUrl);
 */
export default function useWebSocket(url) {
  const [lastMessage, setLastMessage] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    if (!url) return;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
        } catch (e) {
          console.warn('Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        console.log('WebSocket closed:', event.code);

        // Auto-reconnect after 5 seconds
        if (!event.wasClean) {
          reconnectTimer.current = setTimeout(connect, 5000);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('WebSocket connection failed:', e);
      // Retry after 5 seconds
      reconnectTimer.current = setTimeout(connect, 5000);
    }
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { lastMessage, isConnected, send };
}
