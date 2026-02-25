"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

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

type PlatformOption = {
  id: Exclude<Platform, "unknown">;
  label: string;
  icon: string;
  description: string;
};

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

const noopSubscribe = () => () => {};

function useFocusTrap(isOpen: boolean, onClose: () => void) {
  const containerRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    previousFocusRef.current = document.activeElement as HTMLElement;
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
        if (document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable.focus();
        }
      } else {
        if (document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable.focus();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [isOpen, onClose]);

  return containerRef;
}

export default function InstallCenter() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [justInstalled, setJustInstalled] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showIOSHelp, setShowIOSHelp] = useState(false);
  const [isPlatformModalOpen, setIsPlatformModalOpen] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);
  const [platformError, setPlatformError] = useState<string | null>(null);
  const [preferredPlatform, setPreferredPlatform] = useState<Platform | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      const stored = window.localStorage.getItem("wishshare.install-platform");
      if (stored && ["windows", "mac", "linux", "ios", "android"].includes(stored)) {
        return stored as Platform;
      }
    } catch {
      return null;
    }
    return null;
  });
  const platform = useSyncExternalStore<Platform>(noopSubscribe, detectPlatform, () => "unknown");
  const standalone = useSyncExternalStore(noopSubscribe, isStandaloneMode, () => false);

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

  const canInstallAsApp = Boolean(deferredPrompt) && !standalone;
  const isIOSInstallFlow = platform === "ios" && !standalone;
  const canUseShareSheet =
    isIOSInstallFlow &&
    typeof navigator !== "undefined" &&
    typeof navigator.share === "function";
  const platformOptions: PlatformOption[] = [
    { id: "windows", label: "Windows", icon: "🪟", description: "Скачает файл ярлыка .url" },
    { id: "mac", label: "macOS", icon: "🍎", description: "Скачает файл .webloc" },
    { id: "linux", label: "Linux", icon: "🐧", description: "Скачает launcher .desktop" },
    { id: "ios", label: "iOS", icon: "📱", description: "Откроет установку на экран Домой" },
    { id: "android", label: "Android", icon: "🤖", description: "Установит PWA через браузер" }
  ];
  const storageKey = "wishshare.install-platform";

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

  const handleDownloadWebloc = () => {
    const origin = window.location.origin;
    const content =
      `<?xml version="1.0" encoding="UTF-8"?>` +
      `\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">` +
      `\n<plist version="1.0"><dict><key>URL</key><string>${origin}/</string></dict></plist>`;
    const blob = new Blob([content], { type: "application/xml" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "WishShare.webloc";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const handleDownloadDesktop = () => {
    const origin = window.location.origin;
    const content = [
      "[Desktop Entry]",
      "Version=1.0",
      "Type=Application",
      "Name=WishShare",
      "Comment=Открыть WishShare",
      `Exec=xdg-open ${origin}/`,
      `Icon=${origin}/icons/icon-192x192.png`,
      "Terminal=false",
      "Categories=Utility;"
    ].join("\n");
    const blob = new Blob([content], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "wishshare.desktop";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const handleCopyLink = async () => {
    await navigator.clipboard.writeText(window.location.origin);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  const savePreferredPlatform = (value: Platform) => {
    setPreferredPlatform(value);
    try {
      window.localStorage.setItem(storageKey, value);
    } catch {
    }
  };

  const handleConfirmPlatform = async () => {
    if (!selectedPlatform) {
      setPlatformError("Выберите платформу для установки.");
      return;
    }
    savePreferredPlatform(selectedPlatform);
    if (selectedPlatform === "windows") {
      handleDownloadShortcut();
    } else if (selectedPlatform === "mac") {
      handleDownloadWebloc();
    } else if (selectedPlatform === "linux") {
      handleDownloadDesktop();
    } else if (selectedPlatform === "ios") {
      await handleOpenIOSShare();
    } else if (selectedPlatform === "android") {
      if (canInstallAsApp) {
        await handleInstallApp();
      } else {
        setPlatformError("Установка через ярлык недоступна. Используйте кнопку установки приложения.");
        return;
      }
    } else {
      setPlatformError("Платформа не поддерживается.");
      return;
    }
    setIsPlatformModalOpen(false);
  };

  const platformLabel =
    preferredPlatform && preferredPlatform !== "unknown"
      ? platformOptions.find((opt) => opt.id === preferredPlatform)?.label
      : null;
  const modalRef = useFocusTrap(isPlatformModalOpen, () => setIsPlatformModalOpen(false));

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

        <button
          type="button"
          onClick={() => {
            const fallback: Platform | null =
              preferredPlatform ?? (platform !== "unknown" ? platform : null);
            setSelectedPlatform(fallback);
            setPlatformError(null);
            setIsPlatformModalOpen(true);
          }}
          className="btn-ghost text-sm touch-target"
        >
          {platformLabel ? `Скачать ярлык (${platformLabel})` : "Выбрать платформу"}
        </button>

        <button type="button" onClick={handleCopyLink} className="btn-ghost text-sm touch-target">
          {copied ? "Ссылка скопирована" : "Копировать ссылку"}
        </button>
      </div>

      {isPlatformModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
            onClick={() => setIsPlatformModalOpen(false)}
            aria-hidden="true"
          />
          <div
            ref={modalRef}
            className="relative surface-panel-strong p-6 w-full max-w-lg animate-scale-in"
            role="dialog"
            aria-modal="true"
            aria-labelledby="platform-modal-title"
            aria-describedby="platform-modal-description"
          >
            <div className="space-y-2">
              <h3 id="platform-modal-title" className="text-lg font-semibold">Выбор платформы</h3>
              <p id="platform-modal-description" className="text-sm text-[var(--text-secondary)]">
                Выберите устройство, для которого нужно подготовить установку ярлыка.
              </p>
            </div>

            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {platformOptions.map((option) => (
                <label
                  key={option.id}
                  className={`rounded-xl border px-4 py-3 text-sm flex items-center gap-3 cursor-pointer transition ${
                    selectedPlatform === option.id
                      ? "border-emerald-400/60 bg-emerald-400/10"
                      : "border-[var(--line)] bg-black/10 hover:bg-black/20"
                  }`}
                >
                  <input
                    type="radio"
                    name="install-platform"
                    value={option.id}
                    checked={selectedPlatform === option.id}
                    onChange={() => { setSelectedPlatform(option.id); setPlatformError(null); }}
                    className="h-4 w-4 accent-emerald-400"
                  />
                  <span className="text-xl" aria-hidden="true">{option.icon}</span>
                  <span className="flex-1">
                    <span className="font-medium block">{option.label}</span>
                    <span className="text-xs text-[var(--text-secondary)] block">{option.description}</span>
                  </span>
                </label>
              ))}
            </div>

            {platformError ? (
              <div className="mt-3 rounded-xl border border-red-400/40 bg-red-400/10 px-4 py-3 text-sm text-red-100">
                {platformError}
              </div>
            ) : null}

            <div className="mt-5 flex flex-wrap justify-end gap-2">
              <button type="button" onClick={() => setIsPlatformModalOpen(false)} className="btn-ghost text-sm">
                Отмена
              </button>
              <button type="button" onClick={handleConfirmPlatform} className="btn-primary text-sm">
                Установить
              </button>
            </div>
          </div>
        </div>
      ) : null}

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
