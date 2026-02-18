"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "../lib/api";

type Wishlist = {
  id: number;
  slug: string;
  title: string;
  description?: string | null;
  event_date?: string | null;
  privacy?: string;
  is_secret_santa?: boolean;
  access_emails?: string[];
};

type EditWishlistModalProps = {
  wishlist: Wishlist;
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
};

function toInputDate(value?: string | null): string {
  if (!value) return "";
  return value.length >= 10 ? value.slice(0, 10) : value;
}

export default function EditWishlistModal({
  wishlist,
  isOpen,
  onClose,
  onSave
}: EditWishlistModalProps) {
  const [formData, setFormData] = useState({
    title: wishlist.title,
    description: wishlist.description || "",
    event_date: toInputDate(wishlist.event_date),
    privacy: wishlist.privacy || "link_only",
    is_secret_santa: wishlist.is_secret_santa || false,
    access_emails: wishlist.access_emails || []
  });
  const [accessEmailsInput, setAccessEmailsInput] = useState(
    (wishlist.access_emails || []).join("\n")
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parseEmails = (value: string): string[] =>
    value
      .split(/[\n,;]+/)
      .map((email) => email.trim().toLowerCase())
      .filter((email) => email.length > 0);

  useEffect(() => {
    if (isOpen) {
      setFormData({
        title: wishlist.title,
        description: wishlist.description || "",
        event_date: toInputDate(wishlist.event_date),
        privacy: wishlist.privacy || "link_only",
        is_secret_santa: wishlist.is_secret_santa || false,
        access_emails: wishlist.access_emails || []
      });
      setAccessEmailsInput((wishlist.access_emails || []).join("\n"));
      setError(null);
    }
  }, [isOpen, wishlist]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        ...formData,
        access_emails: formData.privacy === "friends" ? parseEmails(accessEmailsInput) : []
      };
      await api.put(`/wishlists/${wishlist.slug}`, payload);
      onSave();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="surface-panel-strong w-full max-w-lg p-6 md:p-7 space-y-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold">Редактирование вишлиста</h2>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Настройте описание, доступ и дату события.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn-ghost px-3 py-2 text-xs"
            aria-label="Закрыть"
          >
            Закрыть
          </button>
        </div>

        {error && (
          <div className="rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="edit-wishlist-title" className="text-sm text-[var(--text-secondary)]">
              Название
            </label>
            <input
              id="edit-wishlist-title"
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              required
            />
          </div>

          <div>
            <label htmlFor="edit-wishlist-description" className="text-sm text-[var(--text-secondary)]">
              Описание
            </label>
            <textarea
              id="edit-wishlist-description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm min-h-[100px] resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="Коротко о событии"
            />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label htmlFor="edit-wishlist-date" className="text-sm text-[var(--text-secondary)]">
                Дата события
              </label>
              <input
                id="edit-wishlist-date"
                type="date"
                value={formData.event_date}
                onChange={(e) => setFormData({ ...formData, event_date: e.target.value })}
                className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div>
              <label htmlFor="edit-wishlist-privacy" className="text-sm text-[var(--text-secondary)]">
                Видимость
              </label>
              <select
                id="edit-wishlist-privacy"
                value={formData.privacy}
                onChange={(e) => setFormData({ ...formData, privacy: e.target.value })}
                className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="link_only">По ссылке</option>
                <option value="friends">Только по email</option>
                <option value="public">Публичный</option>
              </select>
            </div>
          </div>

          {formData.privacy === "friends" && (
            <div>
              <label htmlFor="edit-wishlist-emails" className="text-sm text-[var(--text-secondary)]">
                Email-адреса с доступом
              </label>
              <textarea
                id="edit-wishlist-emails"
                value={accessEmailsInput}
                onChange={(e) => {
                  setAccessEmailsInput(e.target.value);
                  setFormData({ ...formData, access_emails: parseEmails(e.target.value) });
                }}
                className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm min-h-[96px] resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="email1@example.com&#10;email2@example.com"
              />
              <p className="text-xs text-[var(--text-secondary)] mt-2">
                Укажите email в отдельных строках или через запятую.
              </p>
            </div>
          )}

          <label className="flex items-center gap-2 rounded-xl border border-[var(--line)] bg-slate-950/45 px-3 py-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.is_secret_santa}
              onChange={(e) => setFormData({ ...formData, is_secret_santa: e.target.checked })}
              className="rounded border-[var(--line)] bg-slate-900"
            />
            <span className="text-sm">Режим «Тайный Санта»</span>
          </label>

          <div className="flex gap-2 pt-1">
            <button type="button" onClick={onClose} className="btn-ghost flex-1">
              Отмена
            </button>
            <button type="submit" disabled={saving} className="btn-primary flex-1">
              {saving ? "Сохраняем..." : "Сохранить"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
