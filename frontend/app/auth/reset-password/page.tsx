"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../../../lib/api";

export default function ResetPasswordPage() {
  const [token, setToken] = useState<string>("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const tokenFromQuery = new URLSearchParams(window.location.search).get("token");
    if (tokenFromQuery) {
      setToken(tokenFromQuery);
    } else {
      setError("Ссылка недействительна: отсутствует токен");
    }
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!token) {
      setError("Ссылка недействительна");
      return;
    }
    if (password.length < 6) {
      setError("Пароль должен содержать минимум 6 символов");
      return;
    }
    if (password !== confirmPassword) {
      setError("Пароли не совпадают");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await api.post("/auth/reset-password", { token, new_password: password });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сбросить пароль");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen px-4 py-10 grid-mesh">
      <div className="max-w-md mx-auto w-full space-y-6">
        <div className="text-center space-y-2">
          <p className="inline-flex rounded-full border border-[var(--line)] px-3 py-1 text-xs text-[var(--text-secondary)]">
            Новый пароль
          </p>
          <h1 className="text-3xl md:text-4xl font-bold">Обновите пароль</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            После сохранения вы сможете войти с новым паролем
          </p>
        </div>

        <div className="surface-panel-strong p-7 space-y-5">
          {success ? (
            <div className="space-y-4">
              <div className="rounded-xl border border-emerald-400/40 bg-emerald-400/10 px-4 py-3 text-emerald-100 text-sm">
                Пароль успешно изменён.
              </div>
              <Link href="/auth/login" className="btn-primary w-full">
                Перейти ко входу
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
                <label className="text-sm font-medium text-[var(--text-secondary)]">Новый пароль</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Минимум 6 символов"
                  className="w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Подтверждение</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Повторите пароль"
                  className="w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                  required
                />
              </div>
              <button type="submit" disabled={loading || !token} className="btn-primary w-full">
                {loading ? "Сохраняем..." : "Сохранить пароль"}
              </button>
            </form>
          )}
        </div>
      </div>
    </main>
  );
}
