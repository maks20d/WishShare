import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { api, ApiError } from "../lib/api";
import { logger } from "../lib/logger";

export type User = {
  id: number;
  email: string;
  name: string;
  avatar_url?: string | null;
  created_at?: string;
};

export type SessionDays = 7 | 30;

type AuthState = {
  user: User | null;
  loading: boolean;
  sessionChecking: boolean;
  setUser: (user: User | null) => void;
  fetchMe: () => Promise<void>;
  login: (
    email: string,
    password: string,
    rememberMe?: boolean,
    sessionDays?: SessionDays,
  ) => Promise<void>;
  register: (
    name: string,
    email: string,
    password: string,
    rememberMe?: boolean,
    sessionDays?: SessionDays,
  ) => Promise<void>;
  logout: () => Promise<void>;
};

type PersistedAuthState = Pick<AuthState, "user">;

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      loading: false,
      sessionChecking: false,
      setUser: (user) => set({ user }),
      fetchMe: async () => {
        set({ sessionChecking: true });
        try {
          const me = await api.get<User>("/auth/me");
          set({ user: me, sessionChecking: false });
        } catch (error) {
          const err = error as ApiError;
          if (err?.code === "UNAUTHORIZED" || err?.code === "FORBIDDEN") {
            set({ user: null, sessionChecking: false });
            return;
          }
          if (err?.code === "SERVER_ERROR" || err?.code === "NETWORK_ERROR") {
            logger.warn("Auth fetchMe temporary failure; keeping persisted user", {
              code: err?.code,
              message: err?.message
            });
            set({ user: get().user, sessionChecking: false });
            return;
          }
          logger.error("Auth fetchMe failed", err);
          set({ user: get().user, sessionChecking: false });
        }
      },
      login: async (email, password, rememberMe = true, sessionDays = 30) => {
        set({ loading: true });
        try {
          const user = await api.post<User>("/auth/login", {
            email,
            password,
            remember_me: rememberMe,
            session_days: rememberMe ? sessionDays : null,
          });
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
      register: async (name, email, password, rememberMe = true, sessionDays = 30) => {
        set({ loading: true });
        try {
          // /register now sets auth cookies directly — no second /login request needed
          const user = await api.post<User>("/auth/register", {
            name,
            email,
            password,
            remember_me: rememberMe,
            session_days: rememberMe ? sessionDays : null,
          });
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
        try {
          await api.post("/auth/logout");
        } finally {
          set({ user: null, loading: false, sessionChecking: false });
        }
      }
    }),
    {
      name: "wishshare-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state): PersistedAuthState => ({ user: state.user }),
    }
  )
);
