"use client";

import { createContext, useCallback, useContext, useState, ReactNode } from "react";

type ToastType = "success" | "error" | "info";

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void;
  confirm: (message: string) => Promise<boolean>;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let counter = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [confirmState, setConfirmState] = useState<{
    message: string;
    resolve: (v: boolean) => void;
  } | null>(null);

  const toast = useCallback((message: string, type: ToastType = "info") => {
    const id = ++counter;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const confirm = useCallback((message: string): Promise<boolean> => {
    return new Promise((resolve) => {
      setConfirmState({ message, resolve });
    });
  }, []);

  const handleConfirm = (result: boolean) => {
    confirmState?.resolve(result);
    setConfirmState(null);
  };

  const bgClass: Record<ToastType, string> = {
    success: "bg-emerald-600/90 border-emerald-400/40",
    error: "bg-red-600/90 border-red-400/40",
    info: "bg-slate-700/90 border-slate-500/40",
  };

  return (
    <ToastContext.Provider value={{ toast, confirm }}>
      {children}

      {/* Toast stack */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`rounded-xl border px-4 py-3 text-sm text-white shadow-lg backdrop-blur animate-in slide-in-from-right-4 ${bgClass[t.type]}`}
          >
            {t.message}
          </div>
        ))}
      </div>

      {/* Confirm dialog */}
      {confirmState && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="surface-panel-strong p-6 max-w-sm w-full mx-4 space-y-4 shadow-2xl">
            <p className="text-sm text-[var(--text-secondary)]">{confirmState.message}</p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => handleConfirm(false)}
                className="btn-ghost text-sm"
              >
                Отмена
              </button>
              <button
                onClick={() => handleConfirm(true)}
                className="rounded-xl px-4 py-2 text-sm font-medium bg-red-500/20 border border-red-400/40 text-red-200 hover:bg-red-500/30 transition"
              >
                Подтвердить
              </button>
            </div>
          </div>
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
