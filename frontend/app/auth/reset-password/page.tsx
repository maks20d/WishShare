"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../../../lib/api";

function PasswordInput({
  value,
  onChange,
  placeholder,
  id,
}: {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  id: string;
}) {
  const [showPassword, setShowPassword] = useState(false);
  return (
    <div className="relative">
      <input
        type={showPassword ? "text" : "password"}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        id={id}
        className="w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 pr-10 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        required
      />
      <button
        type="button"
        onClick={() => setShowPassword(!showPassword)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
        tabIndex={-1}
      >
        {showPassword ? (
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
            <line x1="1" y1="1" x2="23" y2="23"></line>
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
        )}
      </button>
    </div>
  );
}

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
                <PasswordInput
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Минимум 8 символов, заглавная, строчная, цифра"
                  id="password"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Подтверждение</label>
                <PasswordInput
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Повторите пароль"
                  id="confirmPassword"
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
