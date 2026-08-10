import { useEffect, useRef, useState } from "react";

import { WS_BASE_URL } from "../api";
import type { ConnectionStatus, VesselUpdateMessage } from "../types";

export function useVesselStream(onVesselUpdate: (message: VesselUpdateMessage) => void): ConnectionStatus {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const callbackRef = useRef(onVesselUpdate);

  useEffect(() => {
    callbackRef.current = onVesselUpdate;
  }, [onVesselUpdate]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;
    let heartbeatTimer: number | undefined;
    let disposed = false;

    const connect = () => {
      if (disposed) {
        return;
      }

      setStatus("connecting");
      socket = new WebSocket(`${WS_BASE_URL}/ws/vessels`);

      socket.onopen = () => {
        setStatus("connected");
        heartbeatTimer = window.setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send("ping");
          }
        }, 25000);
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as VesselUpdateMessage;
          if (message.type === "vessel_update") {
            callbackRef.current(message);
          }
        } catch {
          // Ignore malformed messages from development proxies or stale sockets.
        }
      };

      socket.onclose = () => {
        setStatus("disconnected");
        if (heartbeatTimer !== undefined) {
          window.clearInterval(heartbeatTimer);
        }
        if (!disposed) {
          reconnectTimer = window.setTimeout(connect, 2000);
        }
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer !== undefined) {
        window.clearTimeout(reconnectTimer);
      }
      if (heartbeatTimer !== undefined) {
        window.clearInterval(heartbeatTimer);
      }
      socket?.close();
    };
  }, []);

  return status;
}

