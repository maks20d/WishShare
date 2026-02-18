"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../../../lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nextPath, setNextPath] = useState("/dashboard");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const next = new URLSearchParams(window.location.search).get("next");
    if (next && next.startsWith("/")) {
      setNextPath(next);
    }
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.post("/auth/forgot-password", { email });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отправить письмо");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen px-4 py-10 grid-mesh">
      <div className="max-w-md mx-auto w-full space-y-6">
        <div className="text-center space-y-2">
          <p className="inline-flex rounded-full border border-[var(--line)] px-3 py-1 text-xs text-[var(--text-secondary)]">
            Восстановление доступа
          </p>
          <h1 className="text-3xl md:text-4xl font-bold">Сброс пароля</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Отправим ссылку для восстановления на вашу почту
          </p>
        </div>

        <div className="surface-panel-strong p-7 space-y-5">
          {success ? (
            <div className="space-y-4">
              <div className="rounded-xl border border-emerald-400/40 bg-emerald-400/10 px-4 py-3 text-emerald-100 text-sm">
                Если аккаунт с таким email существует, мы отправили ссылку для сброса пароля.
              </div>
              <Link href={`/auth/login?next=${encodeURIComponent(nextPath)}`} className="btn-primary w-full">
                Вернуться ко входу
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="rounded-xl border border-red-400/40 bg-red-400/10 px-4 py-3 text-red-100 text-sm">
                  {error}
                </div>
              )}
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                  required
                />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? "Отправляем..." : "Отправить ссылку"}
              </button>
            </form>
          )}

          {!success && (
            <p className="text-sm text-center text-[var(--text-secondary)]">
              Вспомнили пароль?{" "}
              <Link href={`/auth/login?next=${encodeURIComponent(nextPath)}`} className="font-semibold text-emerald-300">
                Войти
              </Link>
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
