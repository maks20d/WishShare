"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../../lib/api";
import { Gift } from "../../app/wishlist/[slug]/types";
import { useToast } from "../Toast";

interface Props {
  gift: Gift;
  onClose: () => void;
  onRefetch: () => void;
}

const formatRub = (v: number) => new Intl.NumberFormat("ru-RU").format(Math.round(v));

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

export default function ContributionModal({ gift, onClose, onRefetch }: Props) {
  const { toast } = useToast();
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const remaining = gift.price != null ? Math.max(0, gift.price - gift.total_contributions) : null;
  const minimum = gift.price != null ? Math.min(Math.max(gift.price * 0.1, 1), remaining ?? 1) : 1;

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  const modalRef = useFocusTrap(true, handleClose);

  const handleSubmit = async () => {
    const amount = Number.parseFloat(value);
    if (!Number.isFinite(amount) || amount <= 0) { toast("Введите корректную сумму", "error"); return; }
    setSubmitting(true);
    try {
      await api.post(`/gifts/${gift.id}/contribute`, { amount });
      toast(`Вклад ${formatRub(amount)} ₽ внесён!`, "success");
      onRefetch();
      onClose();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Не удалось внести вклад", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
      <div
        ref={modalRef}
        className="surface-panel-strong p-6 max-w-sm w-full space-y-4 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="contribution-modal-title"
      >
        <h3 id="contribution-modal-title" className="text-xl font-semibold">Вклад в «{gift.title}»</h3>
        {remaining != null && (
          <p className="text-sm text-[var(--text-secondary)]">Осталось собрать: {formatRub(remaining)} ₽</p>
        )}
        <input
          type="number" min={minimum} step="any" value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={`Сумма (мин. ${formatRub(minimum)} ₽)`}
          className="w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
          autoFocus
        />
        <div className="flex gap-3">
          <button onClick={onClose} className="btn-ghost flex-1">Отмена</button>
          <button onClick={handleSubmit} disabled={submitting} className="btn-primary flex-1">
            {submitting ? "Отправляем..." : "Внести"}
          </button>
        </div>
      </div>
    </div>
  );
}
