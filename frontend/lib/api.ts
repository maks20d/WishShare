function isLocalDevHost(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

function resolveApiBase(): string {
  const configured =
    process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_BASE_URL;

  if (typeof window !== "undefined") {
    if (configured) {
      if (configured.startsWith("/")) {
        return `${window.location.origin}${configured}`;
      }
      return configured;
    }

    return "/api";
  }

  return configured || "http://localhost:8000";
}

const API_BASE = resolveApiBase();
import { logger } from "./logger";
if (process.env.NODE_ENV !== "production") {
  logger.info("API base URL resolved", { base: API_BASE });
}

export type ApiError = Error & {
  status?: number;
  code?: "UNAUTHORIZED" | "FORBIDDEN" | "SERVER_ERROR" | "NETWORK_ERROR";
  url?: string;
  method?: string;
  requestBody?: unknown;
  responseBody?: unknown;
};

const RETRY_BASE_MS = 300;
const MAX_RETRIES = 2;
const AUTH_REFRESH_PATH = "/auth/refresh";
const AUTH_NO_REFRESH = new Set(["/auth/login", "/auth/register", "/auth/logout", AUTH_REFRESH_PATH]);
let refreshInFlight: Promise<boolean> | null = null;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const shouldAttemptRefresh = (path: string) => !AUTH_NO_REFRESH.has(path);

const refreshAccessToken = async (): Promise<boolean> => {
  if (refreshInFlight) {
    return refreshInFlight;
  }
  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${API_BASE}${AUTH_REFRESH_PATH}`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" }
      });
      return res.ok;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
};

const handleUnauthorizedRedirect = () => {
  // Отключено — не редиректим автоматически при 401
  // Пусть фронтенд сам решает что показывать
  /*
  if (typeof window === "undefined") return;
  const currentPath = `${window.location.pathname}${window.location.search}`;
  if (window.location.pathname.startsWith("/auth/")) return;
  const next = encodeURIComponent(currentPath || "/dashboard");
  window.location.href = `/auth/login?next=${next}`;
  */
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const method = options.method ?? "GET";
  let attempt = 0;
  let lastError: ApiError | null = null;
  let refreshed = false;

  while (attempt <= MAX_RETRIES) {
    try {
      const res = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {})
        },
        credentials: "include"
      });

      if (!res.ok) {
        let message = `HTTP ${res.status}`;
        let responseBody: unknown = undefined;
        try {
          responseBody = await res.clone().json();
          if (
            responseBody &&
            typeof responseBody === "object" &&
            "detail" in responseBody &&
            typeof (responseBody as { detail?: string }).detail === "string"
          ) {
            message = (responseBody as { detail?: string }).detail ?? message;
          }
        } catch {
          try {
            responseBody = await res.clone().text();
            if (typeof responseBody === "string" && responseBody.trim().length > 0) {
              message = responseBody;
            }
          } catch {
            responseBody = undefined;
          }
        }

        if (res.status === 401 && !refreshed && shouldAttemptRefresh(path)) {
          const refreshOk = await refreshAccessToken();
          if (refreshOk) {
            refreshed = true;
            continue;
          }
          handleUnauthorizedRedirect();
        }

        const error: ApiError = new Error(message);
        error.status = res.status;
        error.url = url;
        error.method = method;
        error.requestBody = options.body ? safeJsonParse(options.body) : undefined;
        error.responseBody = responseBody;
        if (res.status === 401) error.code = "UNAUTHORIZED";
        else if (res.status === 403) error.code = "FORBIDDEN";
        else if (res.status >= 500) error.code = "SERVER_ERROR";

        // Don't log 401 as error - it's expected for unauthenticated users
        if (res.status === 401) {
          // Silently handle - guests viewing pages is normal
        } else {
          logger.error("API request failed", {
            url,
            method,
            status: res.status,
            code: error.code,
            requestBody: error.requestBody,
            responseBody,
            stack: error.stack
          });
        }

        if (res.status >= 500 && attempt < MAX_RETRIES) {
          lastError = error;
          attempt += 1;
          await sleep(RETRY_BASE_MS * 2 ** (attempt - 1));
          continue;
        }

        throw error;
      }

      if (res.status === 204) {
        return {} as T;
      }

      const contentType = res.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        return {} as T;
      }

      return res.json() as Promise<T>;
    } catch (err) {
      const known = err as ApiError;
      if (known && typeof known.status === "number") {
        throw known;
      }

      const error: ApiError =
        err instanceof Error ? err : new Error("Network error");
      error.code = error.code ?? "NETWORK_ERROR";
      error.url = url;
      error.method = method;
      error.requestBody = options.body ? safeJsonParse(options.body) : undefined;

      logger.error("API request failed", {
        url,
        method,
        code: error.code,
        requestBody: error.requestBody,
        error: error.message,
        stack: error.stack
      });

      if (attempt < MAX_RETRIES) {
        lastError = error;
        attempt += 1;
        await sleep(RETRY_BASE_MS * 2 ** (attempt - 1));
        continue;
      }

      throw error;
    }
  }

  throw lastError ?? new Error("Unknown API error");
}

function safeJsonParse(payload: BodyInit): unknown {
  if (typeof payload !== "string") return payload;
  try {
    return JSON.parse(payload);
  } catch {
    return payload;
  }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined
    }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined
    }),
  delete: <T>(path: string) =>
    request<T>(path, {
      method: "DELETE"
    })
};
