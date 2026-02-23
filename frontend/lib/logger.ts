type LogPayload = Record<string, unknown> | Error | undefined;

const shouldLog = () => process.env.NODE_ENV !== "production";

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
    console.error(message, payload);
  }
};
