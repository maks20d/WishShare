"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode, useState, useEffect } from "react";
import { useReportWebVitals } from "next/web-vitals";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ToastProvider } from "../components/Toast";
import InstallPrompt from "../components/InstallPrompt";
import { useSwipeNavigation } from "../lib/useSwipeNavigation";
import { registerServiceWorker } from "../lib/registerSW";
import { useAuthStore } from "../store/auth";

/**
 * Inner component that uses the swipe navigation hook
 * This is separated to ensure it's only used on the client side
 */
function SwipeNavigationProvider({ children }: { children: ReactNode }) {
  // Enable iOS-style swipe back navigation
  useSwipeNavigation({
    threshold: 100,
    maxDuration: 300,
    maxVerticalOffset: 100,
    enableSwipeBack: true,
    enableSwipeForward: false,
  });

  return <>{children}</>;
}

function SessionBootstrap() {
  const fetchMe = useAuthStore((state) => state.fetchMe);
  const sessionChecking = useAuthStore((state) => state.sessionChecking);

  useEffect(() => {
    void fetchMe();
  }, [fetchMe]);

  if (!sessionChecking) return null;

  return (
    <div className="fixed top-3 right-3 z-[90] rounded-full border border-[var(--line-strong)] bg-[var(--surface-strong)] px-3 py-1 text-xs text-[var(--text-secondary)] shadow-lg">
      Проверка сессии...
    </div>
  );
}

function WebVitalsReporter() {
  useReportWebVitals((metric) => {
    if (process.env.NODE_ENV !== "production") {
      return;
    }
    const payload = {
      name: metric.name,
      value: metric.value,
      rating: metric.rating,
      id: metric.id,
      navigationType: metric.navigationType
    };
    fetch("/api/metrics/web-vitals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true
    }).catch(() => undefined);
  });

  return null;
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            refetchOnReconnect: false,
          },
        },
      })
  );

  // Register Service Worker for PWA
  useEffect(() => {
    registerServiceWorker();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ErrorBoundary>
          <SwipeNavigationProvider>
            <SessionBootstrap />
            <WebVitalsReporter />
            {children}
            <InstallPrompt />
          </SwipeNavigationProvider>
        </ErrorBoundary>
      </ToastProvider>
    </QueryClientProvider>
  );
}
