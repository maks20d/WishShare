"use client";

import { useEffect, useMemo, useState } from "react";

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

type Platform = "windows" | "mac" | "linux" | "ios" | "android" | "unknown";

function detectPlatform(): Platform {
  if (typeof window === "undefined") return "unknown";
  const ua = window.navigator.userAgent.toLowerCase();
  if (ua.includes("iphone") || ua.includes("ipad") || ua.includes("ipod")) return "ios";
  if (ua.includes("android")) return "android";
  if (ua.includes("windows")) return "windows";
  if (ua.includes("mac")) return "mac";
  if (ua.includes("linux")) return "linux";
  return "unknown";
}

export default function InstallCenter() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [justInstalled, setJustInstalled] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showIOSHelp, setShowIOSHelp] = useState(false);

  useEffect(() => {
    const onBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
    };

    const onAppInstalled = () => {
      setJustInstalled(true);
      setDeferredPrompt(null);
    };

    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    window.addEventListener("appinstalled", onAppInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      window.removeEventListener("appinstalled", onAppInstalled);
    };
  }, []);

  const standalone = useMemo(() => isStandaloneMode(), []);
  const platform = useMemo(() => detectPlatform(), []);
  const canInstallAsApp = Boolean(deferredPrompt) && !standalone;
  const isIOSInstallFlow = platform === "ios" && !standalone;
  const canUseShareSheet =
    isIOSInstallFlow &&
    typeof navigator !== "undefined" &&
    typeof navigator.share === "function";

  const handleInstallApp = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const choice = await deferredPrompt.userChoice;
    if (choice.outcome === "accepted") {
      setJustInstalled(true);
      setDeferredPrompt(null);
    }
  };

  const handleOpenIOSShare = async () => {
    setShowIOSHelp(true);
    if (!canUseShareSheet) return;

    try {
      await navigator.share({
        title: "WishShare",
        text: "Добавьте WishShare на экран Домой",
        url: window.location.href,
      });
    } catch {
      // User dismissed share sheet. Keep help visible.
    }
  };

  const handleDownloadShortcut = () => {
    const origin = window.location.origin;
    const shortcutBody = [
      "[InternetShortcut]",
      `URL=${origin}/`,
      `IconFile=${origin}/icons/icon-192x192.png`,
      "IconIndex=0",
      ""
    ].join("\r\n");

    const blob = new Blob([shortcutBody], { type: "application/internet-shortcut" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "WishShare.url";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const handleCopyLink = async () => {
    await navigator.clipboard.writeText(window.location.origin);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <section className="surface-panel p-4 md:p-5 space-y-3">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-secondary)]">Установка</p>
        <h2 className="text-lg md:text-xl font-semibold">Ярлык и быстрый запуск</h2>
        <p className="text-xs md:text-sm text-[var(--text-secondary)]">
          Закрепите WishShare на рабочем столе или установите как приложение.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2">
        {canInstallAsApp ? (
          <button
            type="button"
            onClick={handleInstallApp}
            className="btn-primary text-sm touch-target"
            title="Установить как приложение"
          >
            {justInstalled ? "Установлено" : "Установить приложение"}
          </button>
        ) : null}

        {isIOSInstallFlow ? (
          <button
            type="button"
            onClick={handleOpenIOSShare}
            className="btn-primary text-sm touch-target"
            title="Открыть системное меню для установки на экран Домой"
          >
            iOS: На экран Домой
          </button>
        ) : null}

        {platform === "windows" ? (
          <button type="button" onClick={handleDownloadShortcut} className="btn-ghost text-sm touch-target">
            Скачать ярлык (Windows)
          </button>
        ) : null}

        <button type="button" onClick={handleCopyLink} className="btn-ghost text-sm touch-target">
          {copied ? "Ссылка скопирована" : "Копировать ссылку"}
        </button>
      </div>

      {isIOSInstallFlow || showIOSHelp ? (
        <div className="rounded-xl border border-[var(--line-strong)] bg-black/20 px-3 py-3 text-xs text-[var(--text-secondary)] space-y-2">
          <p className="font-medium text-[var(--text-primary)]">Установка на iPhone/iPad:</p>
          <ol className="list-decimal pl-4 space-y-1">
            <li>Нажмите кнопку «iOS: На экран Домой» или значок «Поделиться» в браузере.</li>
            <li>В меню выберите «На экран Домой».</li>
            <li>Подтвердите название «WishShare» и нажмите «Добавить».</li>
          </ol>
        </div>
      ) : null}

      <div className="text-xs text-[var(--text-secondary)] rounded-xl border border-[var(--line)] bg-black/15 px-3 py-2">
        {platform === "windows" && "Windows: после скачивания перетащите WishShare.url на рабочий стол и закрепите в панели задач."}
        {platform === "mac" && "macOS: используйте меню браузера «Установить приложение» или перетащите вкладку на рабочий стол."}
        {platform === "linux" && "Linux: используйте «Установить приложение» в браузере или создайте desktop launcher через системное меню."}
        {platform === "ios" && "iOS: добавляйте WishShare через «Поделиться» → «На экран Домой»."}
        {platform === "android" && "Android: используйте кнопку «Установить приложение» или «Добавить на главный экран» в браузере."}
        {platform === "unknown" && "Используйте установку приложения в Edge/Chrome или скачайте ярлык для рабочего стола."}
      </div>
    </section>
  );
}
