"use client";

import { useState } from "react";

const STORAGE_KEY = "wishshare:ios-install-dismissed";

function isIOS(): boolean {
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent);
}

function isSafari(): boolean {
  const ua = window.navigator.userAgent.toLowerCase();
  return ua.includes("safari") && !ua.includes("crios") && !ua.includes("fxios");
}

function isStandaloneMode(): boolean {
  const iosStandalone = "standalone" in window.navigator &&
    Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone);
  const webStandalone = window.matchMedia("(display-mode: standalone)").matches;
  return iosStandalone || webStandalone;
}

export default function IOSInstallPrompt() {
  const [visible, setVisible] = useState(() => {
    if (typeof window === "undefined") return false;
    const dismissed = window.localStorage.getItem(STORAGE_KEY) === "1";
    return !dismissed && isIOS() && isSafari() && !isStandaloneMode();
  });

  const onClose = () => {
    window.localStorage.setItem(STORAGE_KEY, "1");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 z-[70] md:left-auto md:max-w-md">
      <div className="surface-panel-strong border border-[var(--line-strong)] p-4 shadow-xl">
        <p className="text-sm text-[var(--text-primary)]">
          Для установки ярлыка: нажмите «Поделиться» в Safari и выберите «На экран Домой».
        </p>
        <button onClick={onClose} className="btn-ghost mt-3 text-sm">
          Понятно
        </button>
      </div>
    </div>
  );
}
