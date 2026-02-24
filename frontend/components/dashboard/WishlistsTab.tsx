"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useToast } from "../Toast";

type Gift = { id: number };

export type Wishlist = {
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

interface Props {
  onEdit: (wishlist: Wishlist) => void;
  onCreateClick: () => void;
}

const PRIVACY_LABELS: Record<string, string> = {
  link_only: "По ссылке",
  friends: "Только друзья",
  public: "Публичный",
};

const PAGE_SIZE = 20;

export default function WishlistsTab({ onEdit, onCreateClick }: Props) {
  const { toast, confirm } = useToast();
  const [page, setPage] = useState(0);

  const { data: wishlists, refetch, isLoading } = useQuery<Wishlist[]>({
    queryKey: ["my-wishlists", page],
    queryFn: () => api.get(`/wishlists?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`),
  });

  const copyPublicLink = async (slug: string) => {
    const url = `${window.location.origin}/wishlist/${slug}`;
    await navigator.clipboard.writeText(url);
    toast("Публичная ссылка скопирована", "success");
  };

  const handleDelete = async (slug: string, title: string) => {
    const ok = await confirm(
      `Удалить вишлист «${title}»? Подарки и резервы будут удалены без возможности восстановления.`
    );
    if (!ok) return;
    try {
      await api.delete(`/wishlists/${slug}`);
      toast("Вишлист удалён", "success");
      await refetch();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка удаления", "error");
    }
  };

  if (isLoading) {
    return <div className="surface-panel p-6 text-sm text-[var(--text-secondary)]">Загрузка...</div>;
  }

  if (!wishlists || wishlists.length === 0) {
    return (
      <div className="surface-panel p-8 text-center space-y-3">
        <p className="text-lg font-semibold">
          {page > 0 ? "Больше вишлистов нет" : "Пока нет ни одного вишлиста"}
        </p>
        {page > 0 ? (
          <button onClick={() => setPage(0)} className="btn-ghost text-sm">← В начало</button>
        ) : (
          <>
            <p className="text-sm text-[var(--text-secondary)]">Начните с первого списка и поделитесь им с друзьями.</p>
            <button onClick={onCreateClick} className="btn-primary mt-4">Создать первый вишлист</button>
          </>
        )}
      </div>
    );
  }

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">Мои вишлисты</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {wishlists.map((w) => (
          <article key={w.id} className="surface-panel p-5 space-y-4">
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-xl font-semibold leading-tight">{w.title}</h3>
                <span className="text-[11px] rounded-full border border-[var(--line-strong)] px-2 py-1 text-[var(--text-secondary)] whitespace-nowrap">
                  {PRIVACY_LABELS[w.privacy ?? "link_only"] ?? w.privacy}
                </span>
              </div>
              {w.description && <p className="text-sm text-[var(--text-secondary)]">{w.description}</p>}
              <div className="text-xs text-[var(--text-secondary)] flex flex-wrap gap-3">
                <span>🎁 {w.gifts.length}</span>
                {w.event_date && <span>📅 {new Date(w.event_date).toLocaleDateString("ru-RU")}</span>}
                {w.is_secret_santa && <span>🎅 Secret Santa</span>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Link href={`/wishlist/${w.slug}`} className="btn-primary text-sm">Открыть</Link>
              <button type="button" onClick={() => copyPublicLink(w.slug)} className="btn-ghost text-sm">Копировать ссылку</button>
              <button type="button" onClick={() => onEdit(w)} className="btn-ghost text-sm">Редактировать</button>
              <button
                type="button"
                onClick={() => handleDelete(w.slug, w.title)}
                className="rounded-xl px-4 py-3 text-sm font-medium transition border border-red-400/40 bg-red-500/10 text-red-200 hover:bg-red-500/20"
              >
                Удалить
              </button>
            </div>
          </article>
        ))}
      </div>

      {/* Pagination controls */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0}
          className="btn-ghost text-sm disabled:opacity-40"
        >
          ← Назад
        </button>
        <span className="text-sm text-[var(--text-secondary)]">Страница {page + 1}</span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={wishlists.length < PAGE_SIZE}
          className="btn-ghost text-sm disabled:opacity-40"
        >
          Вперёд →
        </button>
      </div>
    </section>
  );
}


  const copyPublicLink = async (slug: string) => {
    const url = `${window.location.origin}/wishlist/${slug}`;
    await navigator.clipboard.writeText(url);
    toast("Публичная ссылка скопирована", "success");
  };

  const handleDelete = async (slug: string, title: string) => {
    const ok = await confirm(
      `Удалить вишлист «${title}»? Подарки и резервы будут удалены без возможности восстановления.`
    );
    if (!ok) return;
    try {
      await api.delete(`/wishlists/${slug}`);
      toast("Вишлист удалён", "success");
      await refetch();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка удаления", "error");
    }
  };

  if (isLoading) {
    return <div className="surface-panel p-6 text-sm text-[var(--text-secondary)]">Загрузка...</div>;
  }

  if (!wishlists || wishlists.length === 0) {
    return (
      <div className="surface-panel p-8 text-center space-y-3">
        <p className="text-lg font-semibold">Пока нет ни одного вишлиста</p>
        <p className="text-sm text-[var(--text-secondary)]">Начните с первого списка и поделитесь им с друзьями.</p>
        <button onClick={onCreateClick} className="btn-primary mt-4">Создать первый вишлист</button>
      </div>
    );
  }

  return (
    <section className="space-y-3">
      <h2 className="text-2xl font-semibold">Мои вишлисты</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {wishlists.map((w) => (
          <article key={w.id} className="surface-panel p-5 space-y-4">
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-xl font-semibold leading-tight">{w.title}</h3>
                <span className="text-[11px] rounded-full border border-[var(--line-strong)] px-2 py-1 text-[var(--text-secondary)] whitespace-nowrap">
                  {PRIVACY_LABELS[w.privacy ?? "link_only"] ?? w.privacy}
                </span>
              </div>
              {w.description && <p className="text-sm text-[var(--text-secondary)]">{w.description}</p>}
              <div className="text-xs text-[var(--text-secondary)] flex flex-wrap gap-3">
                <span>🎁 {w.gifts.length}</span>
                {w.event_date && <span>📅 {new Date(w.event_date).toLocaleDateString("ru-RU")}</span>}
                {w.is_secret_santa && <span>🎅 Secret Santa</span>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Link href={`/wishlist/${w.slug}`} className="btn-primary text-sm">Открыть</Link>
              <button type="button" onClick={() => copyPublicLink(w.slug)} className="btn-ghost text-sm">Копировать ссылку</button>
              <button type="button" onClick={() => onEdit(w)} className="btn-ghost text-sm">Редактировать</button>
              <button
                type="button"
                onClick={() => handleDelete(w.slug, w.title)}
                className="rounded-xl px-4 py-3 text-sm font-medium transition border border-red-400/40 bg-red-500/10 text-red-200 hover:bg-red-500/20"
              >
                Удалить
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
