"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Image from "next/image";
import { api } from "../../lib/api";
import { User, useAuthStore } from "../../store/auth";
import EditWishlistModal from "../../components/EditWishlistModal";
import Tabs from "../../components/Tabs";

type Gift = {
  id: number;
};

type Wishlist = {
  id: number;
  slug: string;
  title: string;
  description?: string | null;
  event_date?: string | null;
  privacy?: "link_only" | "friends" | "public";
  is_secret_santa?: boolean;
  access_emails?: string[];
  gifts: Gift[];
};

function GiftsIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 19a4 4 0 00-6 0m8-9a4 4 0 11-8 0 4 4 0 018 0z"
      />
    </svg>
  );
}

const TABS = [
  { id: "wishlists", label: "Вишлисты", icon: <GiftsIcon /> },
  { id: "create", label: "Создать", icon: <PlusIcon /> },
  { id: "profile", label: "Профиль", icon: <UserIcon /> }
];

export default function DashboardPage() {
  const { user, fetchMe, logout, setUser } = useAuthStore();
  const queryClient = useQueryClient();

  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [privacy, setPrivacy] = useState<"link_only" | "friends" | "public">("link_only");
  const [isSecretSanta, setIsSecretSanta] = useState(false);
  const [accessEmailsInput, setAccessEmailsInput] = useState("");
  const [editingWishlist, setEditingWishlist] = useState<Wishlist | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("wishlists");
  const [profileName, setProfileName] = useState("");
  const [profileAvatar, setProfileAvatar] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [passwordOld, setPasswordOld] = useState("");
  const [passwordNew, setPasswordNew] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  useEffect(() => {
    if (user) {
      setProfileName(user.name || "");
      setProfileAvatar(user.avatar_url || "");
    }
  }, [user]);

  const { data: wishlists, refetch, isLoading } = useQuery<Wishlist[]>({
    queryKey: ["my-wishlists"],
    queryFn: () => api.get("/wishlists")
  });

  const stats = useMemo(() => {
    const list = wishlists || [];
    const gifts = list.reduce((acc, item) => acc + item.gifts.length, 0);
    return {
      totalWishlists: list.length,
      totalGifts: gifts
    };
  }, [wishlists]);

  const resetCreateForm = () => {
    setTitle("");
    setDescription("");
    setEventDate("");
    setPrivacy("link_only");
    setIsSecretSanta(false);
    setAccessEmailsInput("");
  };

  const parseEmails = (value: string): string[] =>
    value
      .split(/[\n,;]+/)
      .map((email) => email.trim().toLowerCase())
      .filter((email) => email.length > 0);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      await api.post("/wishlists", {
        title,
        description: description || null,
        event_date: eventDate || null,
        privacy,
        is_secret_santa: isSecretSanta,
        access_emails: privacy === "friends" ? parseEmails(accessEmailsInput) : []
      });
      resetCreateForm();
      await refetch();
      setActiveTab("wishlists");
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Не удалось создать вишлист");
    } finally {
      setCreating(false);
    }
  };

  const handleEditClick = (wishlist: Wishlist) => {
    setEditingWishlist(wishlist);
    setIsModalOpen(true);
  };

  const handleProfileSave = async (e: FormEvent) => {
    e.preventDefault();
    setProfileSaving(true);
    setProfileError(null);
    try {
      const updated = await api.put<User>("/auth/me", {
        name: profileName,
        avatar_url: profileAvatar || null
      });
      setUser(updated);
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : "Не удалось обновить профиль");
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordChange = async (e: FormEvent) => {
    e.preventDefault();
    setPasswordSaving(true);
    setPasswordError(null);
    setPasswordSuccess(null);
    if (!passwordOld || !passwordNew) {
      setPasswordError("Заполните текущий и новый пароль");
      setPasswordSaving(false);
      return;
    }
    if (passwordNew !== passwordConfirm) {
      setPasswordError("Пароли не совпадают");
      setPasswordSaving(false);
      return;
    }
    try {
      await api.post("/auth/change-password", {
        old_password: passwordOld,
        new_password: passwordNew
      });
      setPasswordOld("");
      setPasswordNew("");
      setPasswordConfirm("");
      setPasswordSuccess("Пароль обновлён");
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : "Не удалось изменить пароль");
    } finally {
      setPasswordSaving(false);
    }
  };

  const handleDeleteClick = async (slug: string) => {
    if (!confirm("Удалить вишлист? Подарки и резервы будут удалены без возможности восстановления.")) {
      return;
    }

    try {
      await api.delete(`/wishlists/${slug}`);
      await refetch();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Ошибка удаления");
    }
  };

  const copyPublicLink = async (slug: string) => {
    const url = `${window.location.origin}/wishlist/${slug}`;
    await navigator.clipboard.writeText(url);
    alert("Публичная ссылка скопирована");
  };

  if (!user) {
    return (
      <main className="min-h-screen px-4 py-10 grid-mesh">
        <div className="max-w-lg mx-auto surface-panel-strong p-8 text-center space-y-5">
          <h1 className="text-3xl font-bold">Доступ к кабинету</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Войдите в аккаунт, чтобы управлять своими вишлистами.
          </p>
          <Link href="/auth/login" className="btn-primary w-full">
            Войти
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-4 py-8 md:py-10 grid-mesh">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="surface-panel-strong p-6 md:p-8 grid gap-6 md:grid-cols-[1fr_auto] md:items-center">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-secondary)]">Управление</p>
            <h1 className="text-3xl md:text-4xl font-semibold">Ваши вишлисты</h1>
            <p className="text-sm text-[var(--text-secondary)] max-w-2xl">
              Создавайте списки, отслеживайте прогресс и делитесь ссылками с друзьями.
            </p>
          </div>
          <div className="flex gap-3 flex-wrap md:justify-end">
            <div className="surface-panel px-4 py-3 min-w-[150px] border border-[var(--line-strong)]">
              <p className="text-xs text-[var(--text-secondary)]">Вишлистов</p>
              <p className="text-2xl font-semibold">{stats.totalWishlists}</p>
            </div>
            <div className="surface-panel px-4 py-3 min-w-[150px] border border-[var(--line-strong)]">
              <p className="text-xs text-[var(--text-secondary)]">Подарков</p>
              <p className="text-2xl font-semibold">{stats.totalGifts}</p>
            </div>
            <button
              onClick={async () => {
                await logout();
                queryClient.clear();
              }}
              className="btn-ghost"
            >
              Выйти
            </button>
          </div>
        </header>

        <Tabs tabs={TABS} defaultTab={activeTab} onChange={setActiveTab}>
          {(tab) => (
            <>
              {tab === "wishlists" && (
                <section className="space-y-3">
                  <h2 className="text-2xl font-semibold">Мои вишлисты</h2>

                  {isLoading ? (
                    <div className="surface-panel p-6 text-sm text-[var(--text-secondary)]">Загрузка...</div>
                  ) : wishlists && wishlists.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {wishlists.map((w) => (
                        <article key={w.id} className="surface-panel p-5 space-y-4">
                          <div className="space-y-2">
                            <div className="flex items-start justify-between gap-3">
                              <h3 className="text-xl font-semibold leading-tight">{w.title}</h3>
                              <span className="text-[11px] rounded-full border border-[var(--line-strong)] px-2 py-1 text-[var(--text-secondary)]">
                                {w.privacy || "link_only"}
                              </span>
                            </div>
                            {w.description && <p className="text-sm text-[var(--text-secondary)]">{w.description}</p>}
                            <div className="text-xs text-[var(--text-secondary)] flex flex-wrap gap-3">
                              <span>🎁 {w.gifts.length}</span>
                              {w.event_date && <span>📅 {new Date(w.event_date).toLocaleDateString("ru-RU")}</span>}
                            </div>
                          </div>

                          <div className="grid grid-cols-2 gap-2">
                            <Link href={`/wishlist/${w.slug}`} className="btn-primary text-sm">
                              Открыть
                            </Link>
                            <button type="button" onClick={() => copyPublicLink(w.slug)} className="btn-ghost text-sm">
                              Копировать ссылку
                            </button>
                            <button type="button" onClick={() => handleEditClick(w)} className="btn-ghost text-sm">
                              Редактировать
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteClick(w.slug)}
                              className="rounded-xl px-4 py-3 text-sm font-medium transition border border-red-400/40 bg-red-500/10 text-red-200 hover:bg-red-500/20"
                            >
                              Удалить
                            </button>
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className="surface-panel p-8 text-center">
                      <p className="text-lg font-semibold">Пока нет ни одного вишлиста</p>
                      <p className="text-sm text-[var(--text-secondary)] mt-2">
                        Начните с первого списка и поделитесь им с друзьями.
                      </p>
                      <button
                        onClick={() => setActiveTab("create")}
                        className="btn-primary mt-4"
                      >
                        Создать первый вишлист
                      </button>
                    </div>
                  )}
                </section>
              )}

              {tab === "create" && (
                <section className="surface-panel p-6 md:p-7 space-y-4">
                  <div>
                    <h2 className="text-2xl font-semibold">Создать новый вишлист</h2>
                    <p className="text-sm text-[var(--text-secondary)] mt-1">
                      Название, описание и уровень доступа можно задать сразу.
                    </p>
                  </div>

                  {createError && (
                    <div className="rounded-xl border border-red-400/40 bg-red-400/10 px-4 py-3 text-red-100 text-sm">
                      {createError}
                    </div>
                  )}

                  <form onSubmit={handleCreate} className="grid gap-3 md:grid-cols-2">
                    <input
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="Название события"
                      className="rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                      required
                    />
                    <input
                      type="date"
                      value={eventDate}
                      onChange={(e) => setEventDate(e.target.value)}
                      className="rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                    />
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Короткое описание (опционально)"
                      className="md:col-span-2 rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm min-h-[96px] focus:outline-none focus:ring-2 focus:ring-emerald-400"
                    />
                    <select
                      value={privacy}
                      onChange={(e) => setPrivacy(e.target.value as "link_only" | "friends" | "public")}
                      className="rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                    >
                      <option value="link_only">По ссылке</option>
                      <option value="friends">Только по email</option>
                      <option value="public">Публичный</option>
                    </select>
                    {privacy === "friends" && (
                      <div className="md:col-span-2">
                        <label className="text-sm text-[var(--text-secondary)]">
                          Email-адреса с доступом
                        </label>
                        <textarea
                          value={accessEmailsInput}
                          onChange={(e) => setAccessEmailsInput(e.target.value)}
                          placeholder="email1@example.com&#10;email2@example.com"
                          className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm min-h-[96px] focus:outline-none focus:ring-2 focus:ring-emerald-400"
                        />
                        <p className="text-xs text-[var(--text-secondary)] mt-2">
                          Укажите email в отдельных строках или через запятую.
                        </p>
                      </div>
                    )}
                    <label className="rounded-xl border border-[var(--line)] px-4 py-3 flex items-center justify-between text-sm">
                      <span className="text-[var(--text-secondary)]">Secret Santa режим</span>
                      <input
                        type="checkbox"
                        checked={isSecretSanta}
                        onChange={(e) => setIsSecretSanta(e.target.checked)}
                        className="h-4 w-4 accent-emerald-400"
                      />
                    </label>
                    <button type="submit" disabled={creating} className="btn-primary md:col-span-2">
                      {creating ? "Создаём..." : "Создать вишлист"}
                    </button>
                  </form>
                </section>
              )}

              {tab === "profile" && (
                <section className="grid gap-4 md:grid-cols-2">
                  <div className="surface-panel p-6 md:p-7 space-y-4">
                    <div>
                      <h2 className="text-2xl font-semibold">Профиль</h2>
                      <p className="text-sm text-[var(--text-secondary)] mt-1">
                        Обновите имя и аватар.
                      </p>
                    </div>

                    {profileError && (
                      <div className="rounded-xl border border-red-400/40 bg-red-400/10 px-4 py-3 text-red-100 text-sm">
                        {profileError}
                      </div>
                    )}

                    <form onSubmit={handleProfileSave} className="space-y-3">
                      <div>
                        <label className="text-sm text-[var(--text-secondary)]">Имя</label>
                        <input
                          value={profileName}
                          onChange={(e) => setProfileName(e.target.value)}
                          className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                          required
                        />
                      </div>
                      <div>
                        <label className="text-sm text-[var(--text-secondary)]">Ссылка на аватар</label>
                        <input
                          value={profileAvatar}
                          onChange={(e) => setProfileAvatar(e.target.value)}
                          placeholder="https://..."
                          className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                        />
                      </div>
                      {profileAvatar && (
                        <div className="h-24 w-24 rounded-xl overflow-hidden border border-[var(--line)] bg-slate-900/40">
                          <Image
                            src={profileAvatar}
                            alt="Аватар"
                            width={96}
                            height={96}
                            className="h-full w-full object-cover"
                            unoptimized
                          />
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
                      <p className="text-sm text-[var(--text-secondary)] mt-1">
                        Обновите пароль для входа.
                      </p>
                    </div>

                    {passwordError && (
                      <div className="rounded-xl border border-red-400/40 bg-red-400/10 px-4 py-3 text-red-100 text-sm">
                        {passwordError}
                      </div>
                    )}

                    {passwordSuccess && (
                      <div className="rounded-xl border border-emerald-400/40 bg-emerald-400/10 px-4 py-3 text-emerald-100 text-sm">
                        {passwordSuccess}
                      </div>
                    )}

                    <form onSubmit={handlePasswordChange} className="space-y-3">
                      <div>
                        <label className="text-sm text-[var(--text-secondary)]">Текущий пароль</label>
                        <input
                          type="password"
                          value={passwordOld}
                          onChange={(e) => setPasswordOld(e.target.value)}
                          className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                        />
                      </div>
                      <div>
                        <label className="text-sm text-[var(--text-secondary)]">Новый пароль</label>
                        <input
                          type="password"
                          value={passwordNew}
                          onChange={(e) => setPasswordNew(e.target.value)}
                          className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                        />
                      </div>
                      <div>
                        <label className="text-sm text-[var(--text-secondary)]">Повторите пароль</label>
                        <input
                          type="password"
                          value={passwordConfirm}
                          onChange={(e) => setPasswordConfirm(e.target.value)}
                          className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                        />
                      </div>
                      <button type="submit" disabled={passwordSaving} className="btn-primary">
                        {passwordSaving ? "Обновляем..." : "Обновить пароль"}
                      </button>
                    </form>
                  </div>
                </section>
              )}
            </>
          )}
        </Tabs>
      </div>

      {editingWishlist && (
        <EditWishlistModal
          wishlist={editingWishlist}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSave={() => refetch()}
        />
      )}
    </main>
  );
}
