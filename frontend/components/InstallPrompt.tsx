"use client";

import { useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "wishshare:install-prompt-dismissed:v2";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

function isStandaloneMode(): boolean {
  if (typeof window === "undefined") return false;
  const iosStandalone =
    "standalone" in window.navigator &&
    Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone);
  const webStandalone = window.matchMedia("(display-mode: standalone)").matches;
  return iosStandalone || webStandalone;
}

function isIOS(): boolean {
  if (typeof window === "undefined") return false;
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent);
}

function supportsShareApi(): boolean {
  if (typeof window === "undefined") return false;
  return typeof navigator.share === "function";
}

export default function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [dismissed, setDismissed] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return window.localStorage.getItem(STORAGE_KEY) === "1";
  });

  useEffect(() => {
    if (typeof window === "undefined") return;

    const onBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
    };

    const onAppInstalled = () => {
      window.localStorage.setItem(STORAGE_KEY, "1");
      setDismissed(true);
      setDeferredPrompt(null);
    };

    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    window.addEventListener("appinstalled", onAppInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      window.removeEventListener("appinstalled", onAppInstalled);
    };
  }, []);

  const canShowIOSInstructions = useMemo(
    () => isIOS() && !isStandaloneMode(),
    []
  );
  const canShowNativeInstall = useMemo(
    () => Boolean(deferredPrompt) && !isStandaloneMode(),
    [deferredPrompt]
  );

  const visible = !dismissed && (canShowNativeInstall || canShowIOSInstructions);

  const closePrompt = () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, "1");
    }
    setDismissed(true);
  };

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const choice = await deferredPrompt.userChoice;
    if (choice.outcome === "accepted") {
      closePrompt();
      return;
    }
    setDeferredPrompt(null);
  };

  const handleOpenShare = async () => {
    if (!supportsShareApi()) return;
    try {
      await navigator.share({
        title: "WishShare",
        text: "Откройте меню и выберите «На экран Домой»",
        url: window.location.href,
      });
    } catch {
      // User cancelled share sheet; keep prompt visible.
    }
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-x-3 bottom-3 z-[80] md:inset-x-auto md:right-4 md:bottom-4 md:w-[380px] safe-area-bottom">
      <div className="surface-panel-strong border border-[var(--line-strong)] p-4 shadow-xl space-y-3">
        <div className="space-y-1">
          <p className="text-sm font-semibold">Установить WishShare</p>
          {canShowNativeInstall ? (
            <p className="text-xs text-[var(--text-secondary)]">
              Добавьте приложение на главный экран для быстрого запуска и полноэкранного режима.
            </p>
          ) : (
            <p className="text-xs text-[var(--text-secondary)]">
              На iPhone/iPad: откройте «Поделиться» и выберите «На экран Домой».
            </p>
          )}
        </div>

        <div className="flex gap-2 flex-wrap">
          {canShowNativeInstall ? (
            <button onClick={handleInstall} className="btn-primary flex-1 touch-target text-sm">
              Установить
            </button>
          ) : null}
          {canShowIOSInstructions && supportsShareApi() ? (
            <button onClick={handleOpenShare} className="btn-ghost flex-1 touch-target text-sm">
              Открыть «Поделиться»
            </button>
          ) : null}
          <button onClick={closePrompt} className="btn-ghost flex-1 touch-target text-sm">
            Позже
          </button>
        </div>
      </div>
    </div>
  );
}
