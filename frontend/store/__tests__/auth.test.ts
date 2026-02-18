import { afterEach, describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";

vi.mock("../../lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn()
  }
}));

import { api, ApiError } from "../../lib/api";
import { useAuthStore } from "../auth";

const resetStore = () => {
  useAuthStore.setState({ user: null, loading: false });
};

describe("auth store", () => {
  afterEach(() => {
    vi.clearAllMocks();
    resetStore();
  });

  it("restores session on fetchMe success", async () => {
    const user = { id: 1, email: "u@example.com", name: "User" };
    (api.get as Mock).mockResolvedValue(user);

    await useAuthStore.getState().fetchMe();

    expect(useAuthStore.getState().user).toEqual(user);
    expect(useAuthStore.getState().loading).toBe(false);
  });

  it("clears session on 401/403", async () => {
    const err = new Error("Unauthorized") as ApiError;
    err.code = "UNAUTHORIZED";
    (api.get as Mock).mockRejectedValue(err);

    await useAuthStore.getState().fetchMe();

    expect(useAuthStore.getState().user).toBeNull();
  });

  it("propagates login errors while stopping loading", async () => {
    const err = new Error("Invalid") as ApiError;
    (api.post as Mock).mockRejectedValue(err);

    await expect(useAuthStore.getState().login("x@y.com", "bad")).rejects.toThrow("Invalid");
    expect(useAuthStore.getState().loading).toBe(false);
  });
});
