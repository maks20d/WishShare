"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode, useState } from "react";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ToastProvider } from "../components/Toast";

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ErrorBoundary>{children}</ErrorBoundary>
      </ToastProvider>
    </QueryClientProvider>
  );
}
