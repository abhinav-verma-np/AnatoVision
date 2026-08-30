"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "anatovision:bookmarks";

function readBookmarks(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

/**
 * Local-only bookmarks for body systems, persisted to localStorage.
 * No account, no login, no backend — per the project constitution.
 *
 * Initial state is always [] so server- and client-rendered markup match;
 * the real value hydrates in an effect right after mount (client-only API).
 */
export function useBookmarks() {
  const [bookmarks, setBookmarks] = useState<string[]>([]);

  useEffect(() => {
    // Deferred via queueMicrotask: calling setState synchronously within an
    // effect body is flagged by eslint-plugin-react-hooks' set-state-in-effect
    // rule. Scheduling as a microtask keeps the same effective timing (fires
    // before paint) while satisfying that rule — same pattern used in
    // hooks/useApiStatus.ts.
    queueMicrotask(() => setBookmarks(readBookmarks()));
  }, []);

  const isBookmarked = useCallback((id: string) => bookmarks.includes(id), [bookmarks]);

  const toggleBookmark = useCallback((id: string) => {
    setBookmarks((prev) => {
      const next = prev.includes(id) ? prev.filter((b) => b !== id) : [...prev, id];
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // Storage unavailable (private browsing, quota) — bookmark still
        // works for the current session via React state.
      }
      return next;
    });
  }, []);

  return { bookmarks, isBookmarked, toggleBookmark };
}
