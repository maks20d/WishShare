"use client";

import { FormEvent, useEffect, useState } from "react";
import Image from "next/image";
import { api } from "../../lib/api";
import { User, useAuthStore } from "../../store/auth";
import { useToast } from "../Toast";

export default function ProfileTab() {
  const { user, setUser } = useAuthStore();
  const { toast } = useToast();

  const [profileName, setProfileName] = useState(user?.name || "");
  const [profileAvatar, setProfileAvatar] = useState(user?.avatar_url || "");
  const [profileSaving, setProfileSaving] = useState(false);

  const [passwordOld, setPasswordOld] = useState("");
  const [passwordNew, setPasswordNew] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);

  useEffect(() => {
    if (user) { setProfileName(user.name || ""); setProfileAvatar(user.avatar_url || ""); }
  }, [user]);

  const handleProfileSave = async (e: FormEvent) => {
    e.preventDefault();
    setProfileSaving(true);
    try {
      const updated = await api.put<User>("/auth/me", { name: profileName, avatar_url: profileAvatar || null });
      setUser(updated);
      toast("Профиль обновлён", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Не удалось обновить профиль", "error");
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordChange = async (e: FormEvent) => {
    e.preventDefault();
    if (!passwordOld || !passwordNew) { toast("Заполните текущий и новый пароль", "error"); return; }
    if (passwordNew.length < 8) { toast("Новый пароль должен быть не менее 8 символов", "error"); return; }
    if (passwordNew !== passwordConfirm) { toast("Пароли не совпадают", "error"); return; }
    setPasswordSaving(true);
    try {
      await api.post("/auth/change-password", { old_password: passwordOld, new_password: passwordNew });
      setPasswordOld(""); setPasswordNew(""); setPasswordConfirm("");
      toast("Пароль успешно обновлён", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Не удалось изменить пароль", "error");
    } finally {
      setPasswordSaving(false);
    }
  };

  return (
    <section className="grid gap-4 md:grid-cols-2">
      <div className="surface-panel p-6 md:p-7 space-y-4">
        <div>
          <h2 className="text-2xl font-semibold">Профиль</h2>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Обновите имя и аватар.</p>
        </div>
        <form onSubmit={handleProfileSave} className="space-y-3">
          <div>
            <label className="text-sm text-[var(--text-secondary)]">Имя</label>
            <input value={profileName} onChange={(e) => setProfileName(e.target.value)} required
              className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400" />
          </div>
          <div>
            <label className="text-sm text-[var(--text-secondary)]">Ссылка на аватар</label>
            <input value={profileAvatar} onChange={(e) => setProfileAvatar(e.target.value)} placeholder="https://..."
              className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400" />
          </div>
          {profileAvatar && (
            <div className="h-24 w-24 rounded-xl overflow-hidden border border-[var(--line)] bg-slate-900/40">
              <Image src={profileAvatar} alt="Аватар" width={96} height={96} className="h-full w-full object-cover" unoptimized />
            </div>
          )}
          <button type="submit" disabled={profileSaving} className="btn-primary">
            {profileSaving ? "Сохраняем..." : "Сохранить профиль"}
          </button>
        </form>
      </div>

      <div className="surface-panel p-6 md:p-7 space-y-4">
        <div>
          <h2 className="text-2xl font-semibold">Смена пароля</h2>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Обновите пароль для входа.</p>
        </div>
        <form onSubmit={handlePasswordChange} className="space-y-3">
          {[
            { label: "Текущий пароль", value: passwordOld, setter: setPasswordOld },
            { label: "Новый пароль (мин. 8 символов)", value: passwordNew, setter: setPasswordNew },
            { label: "Повторите пароль", value: passwordConfirm, setter: setPasswordConfirm },
          ].map(({ label, value, setter }) => (
            <div key={label}>
              <label className="text-sm text-[var(--text-secondary)]">{label}</label>
              <input type="password" value={value} onChange={(e) => setter(e.target.value)}
                className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400" />
            </div>
          ))}
          <button type="submit" disabled={passwordSaving} className="btn-primary">
            {passwordSaving ? "Обновляем..." : "Обновить пароль"}
          </button>
        </form>
      </div>
    </section>
  );
}
