"use client";

import { Component, ReactNode } from "react";
import { logger } from "../lib/logger";

type ErrorBoundaryProps = {
  children: ReactNode;
  fallback?: ReactNode;
};

type ErrorBoundaryState = {
  hasError: boolean;
};

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    logger.error("UI ErrorBoundary", { error: error.message, stack: info.componentStack });
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="mx-auto flex min-h-[40vh] max-w-lg flex-col items-center justify-center gap-3">
            <h2 className="text-xl font-semibold">Что-то пошло не так</h2>
            <p className="text-sm text-neutral-500">Обновите страницу или попробуйте позже.</p>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
