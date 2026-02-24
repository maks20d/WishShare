import { afterEach, describe, expect, it, vi } from "vitest";

import { registerServiceWorker } from "../registerSW";

describe("registerServiceWorker", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("registers immediately when document is already loaded", async () => {
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

    expect(register).toHaveBeenCalledWith("/sw.js", { scope: "/" });
  });
});
