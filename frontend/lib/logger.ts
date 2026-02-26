type LogPayload = Record<string, unknown> | Error | undefined;

const shouldLog = () =>
  process.env.NODE_ENV !== "production" && process.env.NODE_ENV !== "test";

function safeJsonStringify(value: unknown): string {
  try {
    return JSON.stringify(value);
  } catch {
    return "[unserializable]";
  }
}

function trimLogLine(value: string, maxLen: number): string {
  if (value.length <= maxLen) return value;
  return `${value.slice(0, maxLen)}…`;
}

export const logger = {
  debug: (message: string, payload?: LogPayload) => {
    if (shouldLog()) {
      console.debug(`[DEBUG] ${message}`, payload ?? "");
    }
  },
  info: (message: string, payload?: LogPayload) => {
    if (shouldLog()) {
      console.info(message, payload ?? "");
    }
  },
  warn: (message: string, payload?: LogPayload) => {
    if (shouldLog()) {
      console.warn(message, payload ?? "");
    }
  },
  error: (message: string, payload?: LogPayload) => {
    if (payload instanceof Error) {
      const extra =
        payload && typeof payload === "object"
          ? Object.fromEntries(
              Object.entries(payload as unknown as Record<string, unknown>).filter(
                ([, value]) => value !== undefined
              )
            )
          : {};
      const compact = Object.fromEntries(
        Object.entries({
          message: payload.message,
          stack: payload.stack,
          ...extra
        }).filter(([, value]) => value !== undefined)
      );
      const json = safeJsonStringify(compact);
      console.error(`${message} ${trimLogLine(json, 1500)}`, compact);
      return;
    }
    if (!payload || typeof payload !== "object") {
      console.error(message);
      return;
    }

    const compact = Object.fromEntries(
      Object.entries(payload).filter(([, value]) => value !== undefined)
    );

    if (Object.keys(compact).length === 0) {
      console.error(message);
      return;
    }

    const json = safeJsonStringify(compact);
    console.error(`${message} ${trimLogLine(json, 1500)}`, compact);
  }
};
