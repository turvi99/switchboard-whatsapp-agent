import { useEffect, useRef, useState, useCallback } from "react";

// Connects to the backend's /ws pub/sub feed and invokes onEvent for every
// parsed message. Reconnects with backoff on drop so a restarted backend
// (or a flaky tunnel during grading) doesn't permanently sever the live feed.
export function useLiveUpdates(onEvent) {
  const [connected, setConnected] = useState(false);
  const socketRef = useRef(null);
  const retryRef = useRef(0);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${window.location.host}/ws`;
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      setConnected(true);
      retryRef.current = 0;
    };

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        onEventRef.current?.(parsed);
      } catch {
        // Non-JSON frame (e.g. a keepalive ping echo) - ignore.
      }
    };

    socket.onclose = () => {
      setConnected(false);
      const delay = Math.min(1000 * 2 ** retryRef.current, 15000);
      retryRef.current += 1;
      setTimeout(connect, delay);
    };

    socket.onerror = () => {
      socket.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [connect]);

  return { connected };
}
