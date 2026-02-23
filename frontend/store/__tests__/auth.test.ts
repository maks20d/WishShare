import { afterEach, describe, expect, it, vi, beforeEach } from "vitest";
import type { Mock } from "vitest";

vi.mock("../../lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn()
  },
  ApiError: class ApiError extends Error {
    code: string;
    status: number;
    responseBody: unknown;
    constructor(message: string, code: string = "UNKNOWN", status: number = 0, responseBody: unknown = null) {
      super(message);
      this.code = code;
      this.status = status;
      this.responseBody = responseBody;
    }
  }
}));

import { api, ApiError } from "../../lib/api";
import { useAuthStore, type User } from "../auth";

const resetStore = () => {
  useAuthStore.setState({ user: null, loading: false });
};

describe("auth store", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStore();
  });

  afterEach(() => {
    vi.clearAllMocks();
    resetStore();
  });

  describe("initial state", () => {
    it("starts with null user", () => {
      expect(useAuthStore.getState().user).toBeNull();
    });

    it("starts with loading false", () => {
      expect(useAuthStore.getState().loading).toBe(false);
    });
  });

  describe("setUser", () => {
    it("sets user to a valid user object", () => {
      const user: User = {
        id: 1,
        email: "test@example.com",
        name: "Test User"
      };
      
      useAuthStore.getState().setUser(user);
      
      expect(useAuthStore.getState().user).toEqual(user);
    });

    it("sets user to null", () => {
      const user: User = {
        id: 1,
        email: "test@example.com",
        name: "Test User"
      };
      
      useAuthStore.getState().setUser(user);
      useAuthStore.getState().setUser(null);
      
      expect(useAuthStore.getState().user).toBeNull();
    });

    it("updates existing user", () => {
      const user1: User = {
        id: 1,
        email: "test1@example.com",
        name: "Test User 1"
      };
      const user2: User = {
        id: 2,
        email: "test2@example.com",
        name: "Test User 2"
      };
      
      useAuthStore.getState().setUser(user1);
      useAuthStore.getState().setUser(user2);
      
      expect(useAuthStore.getState().user).toEqual(user2);
    });
  });

  describe("fetchMe", () => {
    it("restores session on fetchMe success", async () => {
      const user: User = { id: 1, email: "u@example.com", name: "User" };
      (api.get as Mock).mockResolvedValue(user);

      await useAuthStore.getState().fetchMe();

      expect(useAuthStore.getState().user).toEqual(user);
      expect(useAuthStore.getState().loading).toBe(false);
    });

    it("sets loading to true during fetch", async () => {
      const user: User = { id: 1, email: "u@example.com", name: "User" };
      let resolvePromise: (value: User) => void;
      (api.get as Mock).mockImplementation(() => 
        new Promise((resolve) => { resolvePromise = resolve; })
      );

      const promise = useAuthStore.getState().fetchMe();
      
      // Loading should be true during fetch
      expect(useAuthStore.getState().loading).toBe(true);
      
      // Resolve the promise
      resolvePromise!(user);
      await promise;
      
      expect(useAuthStore.getState().loading).toBe(false);
    });

    it("clears session on 401", async () => {
      const err = new Error("Unauthorized") as ApiError;
      err.code = "UNAUTHORIZED";
      (api.get as Mock).mockRejectedValue(err);

      // Set a user first
      useAuthStore.setState({ user: { id: 1, email: "test@test.com", name: "Test" } });

      await useAuthStore.getState().fetchMe();

      expect(useAuthStore.getState().user).toBeNull();
      expect(useAuthStore.getState().loading).toBe(false);
    });

    it("clears session on 403", async () => {
      const err = new Error("Forbidden") as ApiError;
      err.code = "FORBIDDEN";
      (api.get as Mock).mockRejectedValue(err);

      // Set a user first
      useAuthStore.setState({ user: { id: 1, email: "test@test.com", name: "Test" } });

      await useAuthStore.getState().fetchMe();

      expect(useAuthStore.getState().user).toBeNull();
      expect(useAuthStore.getState().loading).toBe(false);
    });

    it("clears session on SERVER_ERROR", async () => {
      const err = new Error("Server error") as ApiError;
      err.code = "SERVER_ERROR";
      (api.get as Mock).mockRejectedValue(err);

      // Set a user first
      useAuthStore.setState({ user: { id: 1, email: "test@test.com", name: "Test" } });

      await useAuthStore.getState().fetchMe();

      expect(useAuthStore.getState().user).toBeNull();
      expect(useAuthStore.getState().loading).toBe(false);
    });

    it("clears session on unknown error", async () => {
      const err = new Error("Unknown error");
      (api.get as Mock).mockRejectedValue(err);

      // Set a user first
      useAuthStore.setState({ user: { id: 1, email: "test@test.com", name: "Test" } });

      await useAuthStore.getState().fetchMe();

      expect(useAuthStore.getState().user).toBeNull();
      expect(useAuthStore.getState().loading).toBe(false);
    });
  });

  describe("login", () => {
    it("sets user on successful login", async () => {
      const user: User = { id: 1, email: "login@test.com", name: "Login User" };
      (api.post as Mock).mockResolvedValue(user);

      await useAuthStore.getState().login("login@test.com", "password");

      expect(useAuthStore.getState().user).toEqual(user);
      expect(useAuthStore.getState().loading).toBe(false);
    });

    it("sets loading during login", async () => {
      const user: User = { id: 1, email: "login@test.com", name: "Login User" };
      let resolvePromise: (value: User) => void;
      (api.post as Mock).mockImplementation(() => 
        new Promise((resolve) => { resolvePromise = resolve; })
      );

      const promise = useAuthStore.getState().login("login@test.com", "password");
      
      expect(useAuthStore.getState().loading).toBe(true);
      
      resolvePromise!(user);
      await promise;
      
      expect(useAuthStore.getState().loading).toBe(false);
    });

    it("propagates login errors while stopping loading", async () => {
      const err = new Error("Invalid credentials") as ApiError;
      (api.post as Mock).mockRejectedValue(err);

      await expect(
        useAuthStore.getState().login("bad@email.com", "wrong")
      ).rejects.toThrow("Invalid credentials");
      
      expect(useAuthStore.getState().loading).toBe(false);
    });

    it("handles SERVER_ERROR during login", async () => {
      const err = new Error("Server error") as ApiError;
      err.code = "SERVER_ERROR";
      (api.post as Mock).mockRejectedValue(err);

      await expect(
        useAuthStore.getState().login("test@test.com", "password")
      ).rejects.toThrow("Server error");
      
      expect(useAuthStore.getState().loading).toBe(false);
    });

    it("calls api.post with correct parameters", async () => {
      const user: User = { id: 1, email: "test@test.com", name: "Test" };
      (api.post as Mock).mockResolvedValue(user);

      await useAuthStore.getState().login("test@test.com", "mypassword");

      expect(api.post).toHaveBeenCalledWith("/auth/login", {
        email: "test@test.com",
        password: "mypassword"
      });
    });
  });

  describe("register", () => {
    it("registers and logs in user", async () => {
      const user: User = { id: 1, email: "new@test.com", name: "New User" };
      (api.post as Mock)
        .mockResolvedValueOnce(user) // register
        .mockResolvedValueOnce(undefined); // login

      await useAuthStore.getState().register("New User", "new@test.com", "password");

      expect(useAuthStore.getState().user).toEqual(user);
      expect(useAuthStore.getState().loading).toBe(false);
      
      // Check both API calls were made
      expect(api.post).toHaveBeenCalledWith("/auth/register", {
        name: "New User",
        email: "new@test.com",
        password: "password"
      });
      expect(api.post).toHaveBeenCalledWith("/auth/login", {
        email: "new@test.com",
        password: "password"
      });
    });

    it("sets loading during registration", async () => {
      const user: User = { id: 1, email: "new@test.com", name: "New User" };
      let resolveRegister: (value: User) => void;
      (api.post as Mock)
        .mockImplementationOnce(() => new Promise((resolve) => { resolveRegister = resolve; }))
        .mockResolvedValueOnce(undefined);

      const promise = useAuthStore.getState().register("New User", "new@test.com", "password");
      
      expect(useAuthStore.getState().loading).toBe(true);
      
      resolveRegister!(user);
      await promise;
      
      expect(useAuthStore.getState().loading).toBe(false);
    });

    it("propagates registration errors", async () => {
      const err = new Error("Email already exists") as ApiError;
      (api.post as Mock).mockRejectedValue(err);

      await expect(
        useAuthStore.getState().register("User", "existing@test.com", "password")
      ).rejects.toThrow("Email already exists");
      
      expect(useAuthStore.getState().loading).toBe(false);
    });

    it("handles SERVER_ERROR during registration", async () => {
      const err = new Error("Server error") as ApiError;
      err.code = "SERVER_ERROR";
      (api.post as Mock).mockRejectedValue(err);

      await expect(
        useAuthStore.getState().register("User", "test@test.com", "password")
      ).rejects.toThrow("Server error");
      
      expect(useAuthStore.getState().loading).toBe(false);
    });
  });

  describe("logout", () => {
    it("clears user on logout", async () => {
      // Set a user first
      useAuthStore.setState({ 
        user: { id: 1, email: "test@test.com", name: "Test" } 
      });
      
      (api.post as Mock).mockResolvedValue(undefined);

      await useAuthStore.getState().logout();

      expect(useAuthStore.getState().user).toBeNull();
    });

    it("calls logout endpoint", async () => {
      (api.post as Mock).mockResolvedValue(undefined);

      await useAuthStore.getState().logout();

      expect(api.post).toHaveBeenCalledWith("/auth/logout");
    });

    it("clears user even if API call fails", async () => {
      // Set a user first
      useAuthStore.setState({ 
        user: { id: 1, email: "test@test.com", name: "Test" } 
      });
      
      (api.post as Mock).mockRejectedValue(new Error("Network error"));

      await useAuthStore.getState().logout();

      expect(useAuthStore.getState().user).toBeNull();
    });
  });

  describe("User type", () => {
    it("accepts user with all optional fields", () => {
      const user: User = {
        id: 1,
        email: "test@test.com",
        name: "Test User",
        avatar_url: "https://example.com/avatar.jpg",
        created_at: "2024-01-01T00:00:00Z"
      };
      
      useAuthStore.getState().setUser(user);
      
      expect(useAuthStore.getState().user).toEqual(user);
    });

    it("accepts user with null avatar_url", () => {
      const user: User = {
        id: 1,
        email: "test@test.com",
        name: "Test User",
        avatar_url: null
      };
      
      useAuthStore.getState().setUser(user);
      
      expect(useAuthStore.getState().user).toEqual(user);
    });

    it("accepts user without optional fields", () => {
      const user: User = {
        id: 1,
        email: "test@test.com",
        name: "Test User"
      };
      
      useAuthStore.getState().setUser(user);
      
      expect(useAuthStore.getState().user).toEqual(user);
    });
  });

  describe("State persistence", () => {
    it("maintains separate state instances", () => {
      const user1: User = { id: 1, email: "user1@test.com", name: "User 1" };
      const user2: User = { id: 2, email: "user2@test.com", name: "User 2" };
      
      useAuthStore.getState().setUser(user1);
      expect(useAuthStore.getState().user).toEqual(user1);
      
      useAuthStore.getState().setUser(user2);
      expect(useAuthStore.getState().user).toEqual(user2);
    });
  });
});
