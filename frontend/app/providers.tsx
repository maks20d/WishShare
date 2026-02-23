"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode, useState } from "react";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ToastProvider } from "../components/Toast";
import { useSwipeNavigation } from "../lib/useSwipeNavigation";

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

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ErrorBoundary>
          <SwipeNavigationProvider>{children}</SwipeNavigationProvider>
        </ErrorBoundary>
      </ToastProvider>
    </QueryClientProvider>
  );
}
