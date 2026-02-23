import { create } from "zustand";
import { api, ApiError } from "../lib/api";
import { logger } from "../lib/logger";

export type User = {
  id: number;
  email: string;
  name: string;
  avatar_url?: string | null;
  created_at?: string;
};

type AuthState = {
  user: User | null;
  loading: boolean;
  setUser: (user: User | null) => void;
  fetchMe: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,
  setUser: (user) => set({ user }),
  fetchMe: async () => {
    set({ loading: true });
    try {
      const me = await api.get<User>("/auth/me");
      set({ user: me, loading: false });
    } catch (error) {
      const err = error as ApiError;
      if (err?.code === "UNAUTHORIZED" || err?.code === "FORBIDDEN") {
        set({ user: null, loading: false });
        return;
      }
      if (err?.code === "SERVER_ERROR") {
        logger.error("Auth fetchMe failed", err);
        set({ user: null, loading: false });
        return;
      }
      logger.error("Auth fetchMe failed", err);
      set({ user: null, loading: false });
    }
  },
  login: async (email, password) => {
    set({ loading: true });
    try {
      const user = await api.post<User>("/auth/login", { email, password });
      set({ user, loading: false });
    } catch (e) {
      const err = e as ApiError;
      if (err?.code === "SERVER_ERROR") {
        logger.error("Auth login server error", err);
      }
      set({ loading: false });
      throw e;
    }
  },
  register: async (name, email, password) => {
    set({ loading: true });
    try {
      // /register now sets auth cookies directly — no second /login request needed
      const user = await api.post<User>("/auth/register", { name, email, password });
      set({ user, loading: false });
    } catch (e) {
      const err = e as ApiError;
      if (err?.code === "SERVER_ERROR") {
        logger.error("Auth register server error", err);
      }
      set({ loading: false });
      throw e;
    }
  },
  logout: async () => {
    await api.post("/auth/logout");
    set({ user: null });
  }
}));
