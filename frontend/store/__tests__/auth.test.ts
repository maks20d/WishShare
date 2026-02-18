import fs from "node:fs";
import path from "node:path";
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

const skipDirs = new Set([
  "node_modules",
  ".next",
  "coverage",
  "dist",
  "build",
  "test-results",
  ".tmp",
  ".turbo"
]);

const allowedExtensions = new Set([".ts", ".tsx", ".js", ".jsx"]);

const collectSourceFiles = (dir: string, out: string[]) => {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (skipDirs.has(entry.name)) continue;
      collectSourceFiles(path.join(dir, entry.name), out);
      continue;
    }
    const ext = path.extname(entry.name);
    if (allowedExtensions.has(ext)) {
      out.push(path.join(dir, entry.name));
    }
  }
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

  it("disallows raw fetch outside api client", () => {
    const root = process.cwd();
    const apiPath = path.join(root, "lib", "api.ts");
    const files: string[] = [];
    collectSourceFiles(root, files);
    const offenders: string[] = [];
    for (const file of files) {
      if (file === apiPath) continue;
      const content = fs.readFileSync(file, "utf8");
      if (/\bfetch\s*\(/.test(content) || /window\.fetch\s*\(/.test(content)) {
        offenders.push(path.relative(root, file));
      }
    }
    expect(offenders).toEqual([]);
  });
});
