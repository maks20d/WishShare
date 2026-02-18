function isLocalDevHost(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

function resolveWsBase(): string {
  const configured = process.env.NEXT_PUBLIC_WS_BASE_URL;
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_BACKEND_URL;

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const runtimeHost = window.location.hostname;
    const runtimePort = window.location.port;
    const localHost = isLocalDevHost(runtimeHost);
    const isFrontendDevPort = runtimePort === "3000" || runtimePort === "3001" || runtimePort === "5173";

    if (configured) {
      if (configured.startsWith("/")) {
        if (localHost && isFrontendDevPort) {
          return `${protocol}//${runtimeHost}:8000${configured}`;
        }
        return `${protocol}//${runtimeHost}${configured}`;
      }
      try {
        const parsed = new URL(configured.replace(/^ws:/, "http:").replace(/^wss:/, "https:"));
        if (isLocalDevHost(parsed.hostname)) {
          return `${protocol}//${runtimeHost}:${parsed.port || "8000"}${parsed.pathname || "/ws"}`;
        }
      } catch {
        // fallback to configured as-is
      }
      return configured;
    }

    if (apiBase) {
      try {
        const parsed = new URL(apiBase);
        const wsProtocol = parsed.protocol === "https:" ? "wss:" : "ws:";
        return `${wsProtocol}//${parsed.hostname}${parsed.port ? `:${parsed.port}` : ""}/ws`;
      } catch {
        // fallback to default resolution
      }
    }

    if (localHost) {
      return `${protocol}//${runtimeHost}:8000/ws`;
    }
    return `${protocol}//${runtimeHost}/ws`;
  }

  if (configured) {
    return configured;
  }
  if (apiBase) {
    try {
      const parsed = new URL(apiBase);
      const wsProtocol = parsed.protocol === "https:" ? "wss:" : "ws:";
      return `${wsProtocol}//${parsed.host}/ws`;
    } catch {}
  }
  return "ws://localhost:8000/ws";
}

function normalizeSlug(value: string): string {
  let current = value;
  for (let i = 0; i < 2; i += 1) {
    if (!current.includes("%")) {
      break;
    }
    try {
      const decoded = decodeURIComponent(current);
      if (decoded === current) {
        break;
      }
      current = decoded;
    } catch {
      break;
    }
  }
  return current;
}

const WS_BASE = resolveWsBase();
import { logger } from "./logger";
if (process.env.NODE_ENV !== "production") {
  logger.info("WS base URL resolved", { base: WS_BASE });
}

export type WishlistWsMessage = {
  type: string;
  gift: unknown;
};

export type WishlistWsDisconnect = () => void;

export function connectWishlistWs(
  slug: string,
  onMessage: (msg: WishlistWsMessage) => void
): WishlistWsDisconnect {
  let isActive = true;
  let currentSocket: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const connect = () => {
    if (!isActive) {
      return;
    }

    const normalizedSlug = normalizeSlug(slug);
    const socket = new WebSocket(`${WS_BASE}/${encodeURIComponent(normalizedSlug)}`);
    currentSocket = socket;

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WishlistWsMessage;
        onMessage(data);
      } catch {
        // ignore malformed messages
      }
    };

    socket.onerror = () => {
      // browser can report failed handshake in console; we handle reconnect on close
    };

    socket.onclose = (event) => {
      if (!isActive) {
        return;
      }
      // Auth/permission close: do not enter infinite reconnect loop.
      if (event.code === 1008) {
        return;
      }
      reconnectTimer = setTimeout(() => {
        connect();
      }, 2000);
    };
  };

  connect();

  return () => {
    isActive = false;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
    }
    if (currentSocket) {
      currentSocket.close();
      currentSocket = null;
    }
  };
}
