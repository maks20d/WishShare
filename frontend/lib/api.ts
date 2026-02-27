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
function isLocalBackend(base: string): boolean {
  if (base.startsWith("/")) return false;
  try {
    const url = new URL(base);
    return isLocalDevHost(url.hostname) && (url.port === "8000" || url.port === "");
  } catch {
    return false;
  }
}
const IS_LOCAL_BACKEND = isLocalBackend(API_BASE);
import { logger } from "./logger";
if (process.env.NODE_ENV !== "production") {
  logger.info("API base URL resolved", { base: API_BASE });
}

export type ApiError = Error & {
  status?: number;
  code?: "UNAUTHORIZED" | "FORBIDDEN" | "SERVER_ERROR" | "NETWORK_ERROR" | "TIMEOUT";
  url?: string;
  method?: string;
  requestBody?: unknown;
  responseBody?: unknown;
};

const RETRY_BASE_MS = 300;
const MAX_RETRIES = 3;
const REQUEST_TIMEOUT_MS = 15000;
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

function safeJsonStringify(value: unknown): string {
  try {
    return JSON.stringify(value);
  } catch {
    return "";
  }
}

function extractDetailMessage(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim().length > 0) return detail;
  if (Array.isArray(detail)) {
    const messages: string[] = [];
    for (const item of detail) {
      if (!item) continue;
      if (typeof item === "string" && item.trim().length > 0) {
        messages.push(item.trim());
        continue;
      }
      if (typeof item === "object" && "msg" in item) {
        const msg = (item as { msg?: unknown }).msg;
        if (typeof msg === "string" && msg.trim().length > 0) {
          messages.push(msg.trim());
        }
      }
    }
    const unique = Array.from(new Set(messages));
    if (unique.length > 0) return unique.slice(0, 3).join("; ");
  }
  return null;
}

function redactSensitive(value: unknown, depth: number = 0): unknown {
  if (depth > 4) return "[redacted]";
  if (value === null || value === undefined) return value;
  if (typeof value !== "object") return value;
  if (Array.isArray(value)) {
    return value.slice(0, 50).map((item) => redactSensitive(item, depth + 1));
  }
  const obj = value as Record<string, unknown>;
  const result: Record<string, unknown> = {};
  for (const [key, v] of Object.entries(obj)) {
    const normalized = key.toLowerCase();
    if (
      normalized.includes("password") ||
      normalized === "token" ||
      normalized.endsWith("_token") ||
      normalized === "authorization" ||
      normalized === "cookie" ||
      normalized === "set-cookie"
    ) {
      result[key] = "[redacted]";
      continue;
    }
    result[key] = redactSensitive(v, depth + 1);
  }
  return result;
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit & { timeout?: number } = {}
): Promise<Response> {
  const { timeout = REQUEST_TIMEOUT_MS, ...fetchOptions } = options;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    });
    return response;
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      const error: ApiError = new Error(`Request timeout after ${timeout}ms`);
      error.code = "TIMEOUT";
      throw error;
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const method = options.method ?? "GET";
  let attempt = 0;
  let lastError: ApiError | null = null;
  let refreshed = false;

  while (attempt <= MAX_RETRIES) {
    try {
      const res = await fetchWithTimeout(url, {
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
          if (responseBody && typeof responseBody === "object" && "detail" in responseBody) {
            const detail = (responseBody as { detail?: unknown }).detail;
            const extracted = extractDetailMessage(detail);
            if (extracted) {
              message = extracted;
            }
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
        error.requestBody = options.body ? redactSensitive(safeJsonParse(options.body)) : undefined;
        error.responseBody = redactSensitive(responseBody);
        if (res.status === 401) error.code = "UNAUTHORIZED";
        else if (res.status === 403) error.code = "FORBIDDEN";
        else if (res.status >= 500) error.code = "SERVER_ERROR";

        // 401 is expected for unauthenticated users on protected pages.
        if (res.status === 401) {
          // Intentionally silent.
        } else if (res.status === 404 && method === "GET") {
          logger.warn("API request returned 404", { url, method, status: res.status });
        } else {
          const responseBodyPreview =
            typeof responseBody === "string"
              ? responseBody.slice(0, 1500)
              : safeJsonStringify(redactSensitive(responseBody)).slice(0, 1500);
          logger.error("API request failed", {
            url,
            method,
            status: res.status,
            code: error.code,
            requestBody: error.requestBody,
            responseBodyPreview,
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
      if (known && (typeof known.status === "number" || known.code === "TIMEOUT")) {
        if (known.code === "TIMEOUT" && attempt < MAX_RETRIES) {
          lastError = known;
          attempt += 1;
          await sleep(RETRY_BASE_MS * 2 ** (attempt - 1));
          continue;
        }
        throw known;
      }

      const error: ApiError =
        err instanceof Error ? err : new Error("Network error");
      error.code = error.code ?? "NETWORK_ERROR";
      error.url = url;
      error.method = method;
      error.requestBody = options.body ? redactSensitive(safeJsonParse(options.body)) : undefined;
      if (error.code === "NETWORK_ERROR" && IS_LOCAL_BACKEND) {
        const message = "Backend unavailable on http://localhost:8000";
        error.message = message;
        error.responseBody = { detail: message };
      }

      const logPayload = {
        url,
        method,
        code: error.code,
        requestBody: error.requestBody,
        error: error.message,
        responseBody: error.responseBody,
        stack: error.stack
      };
      if (error.code === "NETWORK_ERROR" || error.code === "TIMEOUT") {
        logger.warn("API request failed", logPayload);
      } else {
        logger.error("API request failed", logPayload);
      }

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

async function requestForm<T>(
  path: string,
  options: RequestInit & { timeout?: number } = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const method = options.method ?? "POST";
  let attempt = 0;
  let lastError: ApiError | null = null;
  let refreshed = false;

  while (attempt <= MAX_RETRIES) {
    try {
      const res = await fetchWithTimeout(url, {
        ...options,
        headers: {
          ...(options.headers || {})
        },
        credentials: "include"
      });

      if (!res.ok) {
        let message = `HTTP ${res.status}`;
        let responseBody: unknown = undefined;
        try {
          responseBody = await res.clone().json();
          if (responseBody && typeof responseBody === "object" && "detail" in responseBody) {
            const detail = (responseBody as { detail?: unknown }).detail;
            const extracted = extractDetailMessage(detail);
            if (extracted) {
              message = extracted;
            }
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
        error.responseBody = redactSensitive(responseBody);
        if (res.status === 401) error.code = "UNAUTHORIZED";
        else if (res.status === 403) error.code = "FORBIDDEN";
        else if (res.status >= 500) error.code = "SERVER_ERROR";

        if (res.status === 401) {
        } else if (res.status === 404 && method === "GET") {
          logger.info("API request not found", { url, method, status: res.status });
        } else if (res.status >= 500) {
          logger.error("API request server error", { url, method, status: res.status, message });
        } else {
          logger.warn("API request failed", { url, method, status: res.status, message });
        }

        if (attempt < MAX_RETRIES) {
          lastError = error;
          attempt += 1;
          await sleep(RETRY_BASE_MS * 2 ** (attempt - 1));
          continue;
        }

        throw error;
      }

      const contentType = res.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        return (await res.json()) as T;
      }
      return (await res.text()) as unknown as T;
    } catch (err) {
      const error: ApiError = err instanceof Error ? err : new Error("Network error");
      if (!error.code) {
        error.code = "NETWORK_ERROR";
      }
      error.url = url;
      error.method = method;
      lastError = error;

      if (attempt < MAX_RETRIES) {
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
    }),
  postForm: <T>(path: string, body: FormData) =>
    requestForm<T>(path, {
      method: "POST",
      body
    })
};
