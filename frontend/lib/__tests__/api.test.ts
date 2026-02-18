import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "../api";

const jsonResponse = (status: number, body: unknown) =>
  Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" }
    })
  );

describe("api client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("retries on 500 and succeeds", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementationOnce(() => jsonResponse(500, { detail: "oops" }))
      .mockImplementationOnce(() => jsonResponse(200, { ok: true }));

    const result = await api.get<{ ok: boolean }>("/health");

    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("marks 401 as unauthorized without masking response", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementationOnce(() =>
      jsonResponse(401, { detail: "Unauthorized" })
    );

    try {
      await api.get("/auth/me");
      expect(false).toBe(true);
    } catch (error) {
      const err = error as ApiError;
      expect(err.code).toBe("UNAUTHORIZED");
      expect(err.status).toBe(401);
      expect(err.responseBody).toEqual({ detail: "Unauthorized" });
    }
  });

  it("retries on network error and fails after max attempts", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValue(new Error("Network down"));

    try {
      await api.get("/auth/me");
      expect(false).toBe(true);
    } catch (error) {
      const err = error as ApiError;
      expect(err.code).toBe("NETWORK_ERROR");
      expect(fetchMock).toHaveBeenCalledTimes(3);
    }
  });
});
