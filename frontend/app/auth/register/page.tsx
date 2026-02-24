"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "../../../lib/api";
import { type SessionDays, useAuthStore } from "../../../store/auth";
import { RegisterSkeleton } from "../../../components/Skeleton";

function RegisterContent() {
  const router = useRouter();
  const { register, loading } = useAuthStore();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [sessionDays, setSessionDays] = useState<SessionDays>(30);
  const [error, setError] = useState<string | null>(null);
  const [oauthLoading, setOauthLoading] = useState<"google" | "github" | null>(null);
  const searchParams = useSearchParams();
  const nextParam = searchParams?.get("next");
  const nextPath = nextParam && nextParam.startsWith("/") ? nextParam : "/dashboard";

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await register(name, email, password, rememberMe, sessionDays);
      router.push(nextPath);
    } catch (err) {
      if (err instanceof Error && err.message) {
        setError(err.message);
      } else {
        setError("Не удалось создать аккаунт");
      }
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
      setError(err instanceof Error ? err.message : "Не удалось начать OAuth регистрацию");
      setOauthLoading(null);
    }
  };

  return (
    <main className="min-h-screen px-4 py-10 grid-mesh">
      <div className="max-w-5xl mx-auto w-full grid gap-8 md:grid-cols-[1fr_0.8fr] md:items-start">
        <div className="space-y-6">
          <div className="space-y-3">
            <p className="inline-flex rounded-full border border-[var(--line)] px-3 py-1 text-xs text-[var(--text-secondary)]">
              Регистрация
            </p>
            <h1 className="text-3xl md:text-4xl font-semibold">Создайте профиль</h1>
            <p className="text-sm text-[var(--text-secondary)]">
              Один аккаунт для всех ваших вишлистов и событий
            </p>
          </div>

          <div className="surface-panel-strong p-7 space-y-5">
          {error && (
            <div className="rounded-xl border border-red-400/40 bg-red-400/10 px-4 py-3 text-red-100 text-sm flex items-start gap-2">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Имя</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Как вас зовут?"
                className="w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                required
              />
            </div>

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
              <label className="text-sm font-medium text-[var(--text-secondary)]">Пароль</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Минимум 6 символов"
                className="w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                required
              />
            </div>

            <div className="rounded-xl border border-[var(--line)] bg-slate-900/30 p-3 space-y-3">
              <label className="flex items-center justify-between gap-3 text-sm">
                <span className="text-[var(--text-secondary)]">Запомнить меня</span>
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 accent-emerald-400"
                />
              </label>
              {rememberMe ? (
                <div className="space-y-1">
                  <label className="text-xs text-[var(--text-secondary)]">Срок входа</label>
                  <select
                    value={sessionDays}
                    onChange={(e) => setSessionDays(Number(e.target.value) as SessionDays)}
                    className="w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                  >
                    <option value={7}>7 дней</option>
                    <option value={30}>30 дней</option>
                  </select>
                </div>
              ) : (
                <p className="text-xs text-[var(--text-secondary)]">
                  Сессия закончится при закрытии браузера.
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full mt-2"
            >
              {loading ? "Создаём..." : "Зарегистрироваться"}
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
            Уже зарегистрированы?{" "}
            <Link
              href={`/auth/login?next=${encodeURIComponent(nextPath)}`}
              className="font-semibold text-[var(--accent)] hover:text-[var(--accent-2)]"
            >
              Войти
            </Link>
          </p>
        </div>
        </div>
        <aside className="surface-panel p-7 space-y-5">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-secondary)]">
              Быстрый старт
            </p>
            <h2 className="text-2xl font-semibold">Подготовьте свой первый список</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Добавьте подарки, включите коллективный сбор и отправьте ссылку друзьям.
            </p>
          </div>
          <div className="space-y-3 text-sm text-[var(--text-secondary)]">
            <div className="flex items-start gap-3">
              <span className="text-[var(--accent)]">●</span>
              <span>Автозаполнение подарков по ссылке</span>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-[var(--accent)]">●</span>
              <span>Гибкая приватность: по ссылке, публично, по email</span>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-[var(--accent)]">●</span>
              <span>Подтверждение email для защиты доступов</span>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<RegisterSkeleton />}>
      <RegisterContent />
    </Suspense>
  );
}
