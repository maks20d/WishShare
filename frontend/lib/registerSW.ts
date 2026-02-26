/**
 * Service Worker Registration Module
 * Handles PWA installation and offline capabilities
 */

function isDevelopmentRuntime(): boolean {
  return process.env.NODE_ENV === "development";
}

function isLocalhostRuntime(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1";
}

async function cleanupDevelopmentServiceWorkers(): Promise<void> {
  if (!("serviceWorker" in navigator)) return;

  try {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((registration) => registration.unregister()));
  } catch (error) {
    console.warn("[PWA] Failed to unregister service workers in development:", error);
  }

  if (typeof window !== "undefined" && "caches" in window) {
    try {
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map((name) => caches.delete(name)));
      console.log("[PWA] Development cache cleared");
    } catch (error) {
      console.warn("[PWA] Failed to clear caches in development:", error);
    }
  }
}

export function registerServiceWorker(): () => void {
  if (typeof window === "undefined") {
    return () => {};
  }

  if (!("serviceWorker" in navigator)) {
    console.log("[PWA] Service Worker not supported");
    return () => {};
  }

  // In development mode, service worker caching causes stale Turbopack chunks
  // and frequent ChunkLoadError after hot updates/restarts.
  if (isDevelopmentRuntime() || isLocalhostRuntime()) {
    void cleanupDevelopmentServiceWorkers();
    console.log("[PWA] Service Worker disabled in development mode");
    return () => {};
  }

  let reloading = false;
  // FIX: Store interval ID for cleanup to prevent memory leak
  let updateIntervalId: ReturnType<typeof setInterval> | null = null;

  const doRegister = async () => {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/',
      });

      console.log('[PWA] Service Worker registered:', registration.scope);

      // Проверяем обновления
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // Новая версия доступна
              console.log('[PWA] New version available');
              
              // Можно показать уведомление пользователю
              if (window.confirm('Доступна новая версия приложения. Обновить?')) {
                newWorker.postMessage({ type: 'SKIP_WAITING' });
                window.location.reload();
              }
            }
          });
        }
      });

      // Периодическая проверка обновлений (каждые 60 минут)
      // FIX: Store interval ID for cleanup to prevent memory leak
      updateIntervalId = setInterval(() => {
        registration.update().catch((err) => {
          console.error('[PWA] Failed to check for updates:', err);
        });
      }, 60 * 60 * 1000);

    } catch (error) {
      console.error('[PWA] Service Worker registration failed:', error);
    }
  };

  // If page is already loaded, register immediately.
  if (document.readyState === 'complete') {
    void doRegister();
  } else {
    window.addEventListener('load', () => {
      void doRegister();
    }, { once: true });
  }

  // Обработка сообщений от Service Worker
  navigator.serviceWorker.addEventListener('message', (event) => {
    console.log('[PWA] Message from SW:', event.data);
  });

  // Обработка контроля Service Worker
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloading) return;
    reloading = true;
    console.log('[PWA] Controller changed, reloading...');
    window.location.reload();
  });

  // FIX: Return cleanup function to clear interval and prevent memory leak
  return () => {
    if (updateIntervalId !== null) {
      clearInterval(updateIntervalId);
      updateIntervalId = null;
    }
  };
}

/**
 * Unregister Service Worker
 * Useful for debugging or when user wants to disable offline mode
 */
export async function unregisterServiceWorker(): Promise<boolean> {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return false;
  }

  try {
    const registration = await navigator.serviceWorker.ready;
    const success = await registration.unregister();
    
    if (success) {
      console.log('[PWA] Service Worker unregistered');
    }
    
    return success;
  } catch (error) {
    console.error('[PWA] Failed to unregister Service Worker:', error);
    return false;
  }
}

/**
 * Clear all caches
 * Useful for debugging or when user wants to clear offline data
 */
export async function clearAllCaches(): Promise<boolean> {
  if (typeof window === 'undefined') {
    return false;
  }

  try {
    const cacheNames = await caches.keys();
    await Promise.all(cacheNames.map((name) => caches.delete(name)));
    console.log('[PWA] All caches cleared');
    return true;
  } catch (error) {
    console.error('[PWA] Failed to clear caches:', error);
    return false;
  }
}

/**
 * Check if app is running in standalone mode (PWA)
 */
export function isStandalone(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }

  // iOS Safari
  const isIOSStandalone = 'standalone' in window.navigator && 
    (window.navigator as Navigator & { standalone: boolean }).standalone;
  
  // Android/Chrome
  const isAndroidStandalone = window.matchMedia('(display-mode: standalone)').matches;

  return Boolean(isIOSStandalone || isAndroidStandalone);
}

/**
 * Check if app can be installed (beforeinstallprompt)
 */
export function canInstall(): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof window === 'undefined') {
      resolve(false);
      return;
    }

    const handler = (e: Event) => {
      e.preventDefault();
      window.removeEventListener('beforeinstallprompt', handler);
      resolve(true);
    };

    window.addEventListener('beforeinstallprompt', handler);

    // Timeout after 1 second
    setTimeout(() => {
      window.removeEventListener('beforeinstallprompt', handler);
      resolve(false);
    }, 1000);
  });
}

/**
 * Get PWA installation status
 */
export function getPWAStatus(): {
  isStandalone: boolean;
  hasServiceWorker: boolean;
  isOnline: boolean;
} {
  return {
    isStandalone: isStandalone(),
    hasServiceWorker: 'serviceWorker' in navigator,
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
  };
}
