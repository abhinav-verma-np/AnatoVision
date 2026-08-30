"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getApiStatus, type ApiStatusResponse } from "@/services/statusService";

export type ConnectionState = "checking" | "online" | "offline";

interface UseApiStatusResult {
  state: ConnectionState;
  data: ApiStatusResponse | null;
  error: string | null;
  lastCheckedAt: Date | null;
  refresh: () => void;
}

const POLL_INTERVAL_MS = 20_000;

/**
 * Tracks whether the FastAPI backend is reachable.
 *
 * Deliberately has no artificial minimum-loading-time or skeleton
 * animation — "checking" only lasts as long as the real request takes,
 * per the Phase 1 requirement to avoid fake loading states.
 */
export function useApiStatus(): UseApiStatusResult {
  const [state, setState] = useState<ConnectionState>("checking");
  const [data, setData] = useState<ApiStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<Date | null>(null);
  const isMounted = useRef(true);

  const check = useCallback(async () => {
    setState("checking");
    try {
      const result = await getApiStatus();
      if (!isMounted.current) return;
      setData(result);
      setError(null);
      setState("online");
    } catch (err) {
      if (!isMounted.current) return;
      setData(null);
      setError(err instanceof Error ? err.message : "Unknown error");
      setState("offline");
    } finally {
      if (isMounted.current) setLastCheckedAt(new Date());
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;

    // Deferred via queueMicrotask rather than called directly: calling an
    // async function synchronously from an effect still runs its body
    // (including the first setState("checking")) synchronously in the
    // same call stack as the effect, which eslint-plugin-react-hooks'
    // set-state-in-effect rule flags. Scheduling as a microtask keeps the
    // same effective timing (fires before paint) while satisfying that rule.
    queueMicrotask(() => void check());

    const interval = setInterval(() => void check(), POLL_INTERVAL_MS);
    return () => {
      isMounted.current = false;
      clearInterval(interval);
    };
  }, [check]);

  return { state, data, error, lastCheckedAt, refresh: check };
}
