import { normalizeRouteParam } from "./routeParams";

function isLocalDevHost(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

function resolveWsBase(): string {
  const configured = (process.env.NEXT_PUBLIC_WS_BASE_URL || "").trim();
  const apiBase = (process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "").trim();

  // Отдаём приоритет явной конфигурации: позволяет обходить ограничения прокси (например, Vercel не проксирует WS Upgrade).
  if (configured) {
    try {
      const url = new URL(configured.replace(/^ws:/, "http:").replace(/^wss:/, "https:"));
      const wsProtocol = url.protocol === "https:" ? "wss:" : "ws:";
      const base = `${wsProtocol}//${url.host}${url.pathname}`;
      return base.endsWith("/ws") ? base : `${base}/ws`;
    } catch {
      // Если задан относительный путь, используем как is (например, "/ws")
      return configured;
    }
  }

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const runtimeHost = window.location.hostname;
    const runtimePort = window.location.port;
    const localHost = isLocalDevHost(runtimeHost);
    const isFrontendDevPort =
      runtimePort === "3000" || runtimePort === "3001" || runtimePort === "5173";

    // Локальная разработка: стучимся напрямую на бекенд порт 8000
    if (localHost && isFrontendDevPort) {
      return `${protocol}//${runtimeHost}:8000/ws`;
    }

    // Прод: если указан API_BASE абсолютным URL — строим WS к бекенду напрямую
    if (apiBase) {
      try {
        const parsed = new URL(apiBase);
        const wsProtocol = parsed.protocol === "https:" ? "wss:" : "ws:";
        return `${wsProtocol}//${parsed.host}/ws`;
      } catch {
        // невалидный URL — падаем на same-origin
      }
    }

    // Fallback: same-origin (может не работать за прокси, если не поддерживается Upgrade)
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
  let shouldCloseOnOpen = false;

  const connect = () => {
    if (!isActive) {
      return;
    }

    const normalizedSlug = normalizeRouteParam(slug);
    if (!normalizedSlug) {
      return;
    }

    const socket = new WebSocket(`${WS_BASE}/${encodeURIComponent(normalizedSlug)}`);
    currentSocket = socket;

    socket.onopen = () => {
      if (!isActive || shouldCloseOnOpen) {
        socket.close();
      }
    };

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
    shouldCloseOnOpen = true;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
    }
    if (currentSocket) {
      if (
        currentSocket.readyState === WebSocket.OPEN ||
        currentSocket.readyState === WebSocket.CLOSING
      ) {
        currentSocket.close();
      }
      currentSocket = null;
    }
  };
}
