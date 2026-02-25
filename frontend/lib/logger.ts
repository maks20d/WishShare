type LogPayload = Record<string, unknown> | Error | undefined;

const shouldLog = () =>
  process.env.NODE_ENV !== "production" && process.env.NODE_ENV !== "test";

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
      console.error(message, { message: payload.message, stack: payload.stack });
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

    console.error(message, compact);
  }
};
