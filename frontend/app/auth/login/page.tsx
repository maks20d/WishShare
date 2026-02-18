"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "../../../lib/api";
import { useAuthStore } from "../../../store/auth";

function LoginContent() {
  const router = useRouter();
  const { login, loading } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [oauthLoading, setOauthLoading] = useState<"google" | "github" | null>(null);
  const searchParams = useSearchParams();
  const nextParam = searchParams?.get("next");
  const nextPath = nextParam && nextParam.startsWith("/") ? nextParam : "/dashboard";
  const verifiedParam = searchParams?.get("verified");
  const verifiedMessage =
    verifiedParam === "1"
      ? "Email подтверждён. Теперь можно войти."
      : verifiedParam === "0"
        ? "Ссылка подтверждения недействительна или устарела."
        : null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await login(email, password);
      router.push(nextPath);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Неверный email или пароль";
      setError(errorMessage);
    }
  };

  const handleOAuth = async (provider: "google" | "github") => {
    setError(null);
    setOauthLoading(provider);
    try {
      const data = await api.get<{ url: string }>(
        `/auth/oauth/${provider}?next=${encodeURIComponent(nextPath)}`
      );
      window.location.href = data.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось начать OAuth вход");
      setOauthLoading(null);
    }
  };

  return (
    <main className="min-h-screen px-4 py-10 grid-mesh">
      <div className="max-w-5xl mx-auto w-full grid gap-8 md:grid-cols-[1fr_0.8fr] md:items-start">
        <div className="space-y-6">
          <div className="space-y-3">
            <p className="inline-flex rounded-full border border-[var(--line)] px-3 py-1 text-xs text-[var(--text-secondary)]">
              Авторизация
            </p>
            <h1 className="text-3xl md:text-4xl font-semibold">С возвращением</h1>
            <p className="text-sm text-[var(--text-secondary)]">
              Войдите, чтобы управлять вишлистами и резервами
            </p>
          </div>

          <div className="surface-panel-strong p-7 space-y-5">
          {verifiedMessage && (
            <div className="rounded-xl border border-emerald-400/40 bg-emerald-400/10 px-4 py-3 text-emerald-100 text-sm">
              {verifiedMessage}
            </div>
          )}
          {error && (
            <div className="rounded-xl border border-red-400/40 bg-red-400/10 px-4 py-3 text-red-100 text-sm flex items-start gap-2">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                className="w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                required
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Пароль</label>
                <Link
                  href={`/auth/forgot-password?next=${encodeURIComponent(nextPath)}`}
                  className="text-xs text-[var(--accent)] hover:text-[var(--accent-2)]"
                >
                  Забыли пароль?
                </Link>
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full mt-2"
            >
              {loading ? "Входим..." : "Войти"}
            </button>
          </form>

          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="h-px bg-[var(--line)] flex-1" />
              <span className="text-xs text-[var(--text-secondary)]">или через</span>
              <div className="h-px bg-[var(--line)] flex-1" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleOAuth("google")}
                disabled={oauthLoading !== null}
                className="btn-ghost text-sm"
              >
                {oauthLoading === "google" ? "..." : "Google"}
              </button>
              <button
                type="button"
                onClick={() => handleOAuth("github")}
                disabled={oauthLoading !== null}
                className="btn-ghost text-sm"
              >
                {oauthLoading === "github" ? "..." : "GitHub"}
              </button>
            </div>
          </div>

          <p className="text-sm text-center text-[var(--text-secondary)]">
            Нет аккаунта?{" "}
            <Link
              href={`/auth/register?next=${encodeURIComponent(nextPath)}`}
              className="font-semibold text-[var(--accent)] hover:text-[var(--accent-2)]"
            >
              Зарегистрироваться
            </Link>
          </p>
        </div>
        </div>
        <aside className="surface-panel p-7 space-y-5">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-secondary)]">
              Почему WishShare
            </p>
            <h2 className="text-2xl font-semibold">Управляйте сюрпризами</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Делитесь ссылкой, смотрите прогресс сборов и сохраняйте интригу для себя.
            </p>
          </div>
          <div className="space-y-3 text-sm text-[var(--text-secondary)]">
            <div className="flex items-start gap-3">
              <span className="text-[var(--accent)]">●</span>
              <span>Реалтайм-обновления без перезагрузки страницы</span>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-[var(--accent)]">●</span>
              <span>Гибкий режим приватности и доступ по email</span>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-[var(--accent)]">●</span>
              <span>Коллективные сборы с контролем минимального вклада</span>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LoginContent />
    </Suspense>
  );
}
