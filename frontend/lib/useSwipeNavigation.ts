"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useCallback } from "react";

interface SwipeNavigationOptions {
  /** Minimum swipe distance in pixels to trigger navigation (default: 100) */
  threshold?: number;
  /** Maximum time in ms for a swipe gesture (default: 300) */
  maxDuration?: number;
  /** Maximum vertical movement allowed during horizontal swipe (default: 100) */
  maxVerticalOffset?: number;
  /** Enable swipe back gesture (default: true) */
  enableSwipeBack?: boolean;
  /** Enable swipe forward gesture (default: false - usually not needed) */
  enableSwipeForward?: boolean;
}

/**
 * Hook for iOS-style swipe navigation
 * Swipe right to go back, swipe left to go forward (if enabled)
 */
export function useSwipeNavigation(options: SwipeNavigationOptions = {}) {
  const {
    threshold = 100,
    maxDuration = 300,
    maxVerticalOffset = 100,
    enableSwipeBack = true,
    enableSwipeForward = false,
  } = options;

  const router = useRouter();
  const touchStartX = useRef(0);
  const touchStartY = useRef(0);
  const touchStartTime = useRef(0);
  const isSwiping = useRef(false);

  const handleTouchStart = useCallback((e: TouchEvent) => {
    // Only track swipes that start from the left edge for back navigation
    const touch = e.changedTouches[0];
    touchStartX.current = touch.screenX;
    touchStartY.current = touch.screenY;
    touchStartTime.current = Date.now();
    isSwiping.current = true;
  }, []);

  const handleTouchEnd = useCallback(
    (e: TouchEvent) => {
      if (!isSwiping.current) return;
      isSwiping.current = false;

      const touch = e.changedTouches[0];
      const touchEndX = touch.screenX;
      const touchEndY = touch.screenY;
      const duration = Date.now() - touchStartTime.current;

      // Calculate distances
      const horizontalDiff = touchStartX.current - touchEndX;
      const verticalDiff = Math.abs(touchStartY.current - touchEndY);

      // Check if it's a valid horizontal swipe
      if (
        duration > maxDuration ||
        verticalDiff > maxVerticalOffset
      ) {
        return;
      }

      // Swipe right to go back (negative diff means swipe right)
      if (enableSwipeBack && horizontalDiff < -threshold) {
        // Check if swipe started from left edge (within 50px)
        if (touchStartX.current < 50) {
          router.back();
        }
      }

      // Swipe left to go forward (positive diff means swipe left)
      if (enableSwipeForward && horizontalDiff > threshold) {
        router.forward();
      }
    },
    [
      router,
      threshold,
      maxDuration,
      maxVerticalOffset,
      enableSwipeBack,
      enableSwipeForward,
    ]
  );

  const handleTouchCancel = useCallback(() => {
    isSwiping.current = false;
  }, []);

  useEffect(() => {
    // Only enable on touch devices
    if (typeof window === "undefined" || !("ontouchstart" in window)) {
      return;
    }

    window.addEventListener("touchstart", handleTouchStart, { passive: true });
    window.addEventListener("touchend", handleTouchEnd, { passive: true });
    window.addEventListener("touchcancel", handleTouchCancel, { passive: true });

    return () => {
      window.removeEventListener("touchstart", handleTouchStart);
      window.removeEventListener("touchend", handleTouchEnd);
      window.removeEventListener("touchcancel", handleTouchCancel);
    };
  }, [handleTouchStart, handleTouchEnd, handleTouchCancel]);
}

export default useSwipeNavigation;
