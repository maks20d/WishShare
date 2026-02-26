import { afterEach, describe, expect, it, vi } from "vitest";

import { registerServiceWorker } from "../registerSW";

describe("registerServiceWorker", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("skips registration in development on localhost", async () => {
    const register = vi.fn().mockResolvedValue({
      scope: "/",
      installing: null,
      addEventListener: vi.fn(),
      update: vi.fn().mockResolvedValue(undefined),
    });

    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: {
        register,
        addEventListener: vi.fn(),
      },
    });

    Object.defineProperty(document, "readyState", {
      configurable: true,
      value: "complete",
    });

    registerServiceWorker();
    await Promise.resolve();

    expect(register).not.toHaveBeenCalled();
  });

  it("registers immediately in production on non-localhost", async () => {
    const register = vi.fn().mockResolvedValue({
      scope: "/",
      installing: null,
      addEventListener: vi.fn(),
      update: vi.fn().mockResolvedValue(undefined),
    });

    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: {
        register,
        addEventListener: vi.fn(),
      },
    });

    Object.defineProperty(document, "readyState", {
      configurable: true,
      value: "complete",
    });

    const prevEnv = process.env.NODE_ENV;
    const prevLocation = window.location;
    try {
      process.env.NODE_ENV = "production";
      Object.defineProperty(window, "location", {
        configurable: true,
        value: new URL("https://example.com"),
      });
      registerServiceWorker();
      await Promise.resolve();
    } finally {
      process.env.NODE_ENV = prevEnv;
      Object.defineProperty(window, "location", {
        configurable: true,
        value: prevLocation,
      });
    }

    expect(register).toHaveBeenCalledWith("/sw.js", { scope: "/" });
  });
});
