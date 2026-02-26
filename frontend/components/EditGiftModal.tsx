"use client";

import { FormEvent, useEffect, useState, useRef, useCallback } from "react";
import Image from "next/image";
import { api } from "../lib/api";

type Gift = {
  id: number;
  title: string;
  url?: string | null;
  price?: number | null;
  image_url?: string | null;
  is_collective: boolean;
  is_private: boolean;
};

type EditGiftModalProps = {
  gift: Gift;
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
};

/**
 * Focus trap hook for accessibility
 * FIX: Added focus trap to prevent focus from escaping modal dialog
 */
function useFocusTrap(isOpen: boolean, onClose: () => void) {
  const containerRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    // Store the previously focused element
    previousFocusRef.current = document.activeElement as HTMLElement;

    // Focus the first focusable element in the modal
    const focusableElements = containerRef.current?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusableElements && focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }

      if (e.key !== "Tab") return;

      const focusables = containerRef.current?.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (!focusables || focusables.length === 0) return;

      const firstFocusable = focusables[0];
      const lastFocusable = focusables[focusables.length - 1];

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable.focus();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      // Restore focus when modal closes
      previousFocusRef.current?.focus();
    };
  }, [isOpen, onClose]);

  return containerRef;
}

export default function EditGiftModal({
  gift,
  isOpen,
  onClose,
  onSave
}: EditGiftModalProps) {
  const [formData, setFormData] = useState({
    title: gift.title,
    url: gift.url || "",
    image_url: gift.image_url || "",
    price: gift.price ? String(gift.price) : "",
    is_collective: gift.is_collective,
    is_private: gift.is_private
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  const modalRef = useFocusTrap(isOpen, handleClose);

  useEffect(() => {
    if (isOpen) {
      setFormData({
        title: gift.title,
        url: gift.url || "",
        image_url: gift.image_url || "",
        price: gift.price ? String(gift.price) : "",
        is_collective: gift.is_collective,
        is_private: gift.is_private
      });
      setError(null);
    }
  }, [isOpen, gift]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const priceValue = formData.price.trim().length > 0 ? Number.parseFloat(formData.price) : undefined;
    if (priceValue !== undefined && (!Number.isFinite(priceValue) || priceValue <= 0)) {
      setSaving(false);
      setError("Цена должна быть больше 0");
      return;
    }

    try {
      await api.put(`/gifts/${gift.id}`, {
        title: formData.title,
        url: formData.url || undefined,
        image_url: formData.image_url || undefined,
        price: priceValue,
        is_collective: formData.is_collective,
        is_private: formData.is_private
      });
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
      <div
        ref={modalRef}
        className="surface-panel-strong w-full max-w-lg p-6 md:p-7 space-y-5"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-gift-modal-title"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="edit-gift-modal-title" className="text-2xl font-semibold">Редактирование подарка</h2>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Изменения сразу увидят участники вишлиста.
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
            <label htmlFor="edit-gift-title" className="text-sm text-[var(--text-secondary)]">
              Название
            </label>
            <input
              id="edit-gift-title"
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              required
            />
          </div>

          <div>
            <label htmlFor="edit-gift-url" className="text-sm text-[var(--text-secondary)]">
              Ссылка на товар
            </label>
            <input
              id="edit-gift-url"
              type="url"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="https://example.com"
            />
          </div>

          <div>
            <label htmlFor="edit-gift-price" className="text-sm text-[var(--text-secondary)]">
              Цена
            </label>
            <input
              id="edit-gift-price"
              type="number"
              min={1}
              step={1}
              value={formData.price}
              onChange={(e) => setFormData({ ...formData, price: e.target.value })}
              className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="0"
            />
          </div>

          <div>
            <label htmlFor="edit-gift-image-url" className="text-sm text-[var(--text-secondary)]">
              Ссылка на изображение
            </label>
            <input
              id="edit-gift-image-url"
              type="url"
              value={formData.image_url}
              onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
              className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="https://example.com/image.jpg"
            />
          </div>

          {formData.image_url && (
            <div className="h-32 rounded-xl overflow-hidden border border-[var(--line)] bg-slate-900/40 relative">
              <Image
                src={formData.image_url}
                alt="Предпросмотр изображения"
                fill
                sizes="200px"
                className="object-cover"
                unoptimized
              />
            </div>
          )}

          <div className="grid gap-2 md:grid-cols-2">
            <label className="flex items-center gap-2 rounded-xl border border-[var(--line)] bg-slate-950/45 px-3 py-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_collective}
                onChange={(e) => setFormData({ ...formData, is_collective: e.target.checked })}
                className="rounded border-[var(--line)] bg-slate-900"
              />
              <span className="text-sm">Коллективный сбор</span>
            </label>

            <label className="flex items-center gap-2 rounded-xl border border-[var(--line)] bg-slate-950/45 px-3 py-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_private}
                onChange={(e) => setFormData({ ...formData, is_private: e.target.checked })}
                className="rounded border-[var(--line)] bg-slate-900"
              />
              <span className="text-sm">Приватный подарок</span>
            </label>
          </div>

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
