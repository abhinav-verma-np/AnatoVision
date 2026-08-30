"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { loadManifest, type Manifest } from "@/lib/manifest";

export type ManifestStatus = "loading" | "ready" | "error";

interface UseManifestResult {
  manifest: Manifest | null;
  status: ManifestStatus;
  error: string | null;
  refresh: () => void;
}

/**
 * Loads frontend/public/models/manifest.json.
 *
 * Safe to call from several components at once (SearchBar, ViewerWorkspace,
 * RightInspector all use this independently) — loadManifest() caches at
 * module scope, so only the very first call actually hits the network;
 * every other caller (here or elsewhere) resolves from cache immediately.
 */
export function useManifest(): UseManifestResult {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [status, setStatus] = useState<ManifestStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const isMounted = useRef(true);

  const load = useCallback(async () => {
    setStatus("loading");
    try {
      const result = await loadManifest();
      if (!isMounted.current) return;
      setManifest(result);
      setError(null);
      setStatus("ready");
    } catch (err) {
      if (!isMounted.current) return;
      setManifest(null);
      setError(err instanceof Error ? err.message : "Unknown error loading manifest");
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;

    // Deferred via queueMicrotask: calling an async function synchronously
    // from an effect still runs its body (including the first
    // setStatus("loading")) synchronously in the same call stack as the
    // effect, which eslint-plugin-react-hooks' set-state-in-effect rule
    // flags. Scheduling as a microtask keeps the same effective timing
    // while satisfying that rule — same pattern as hooks/useApiStatus.ts.
    queueMicrotask(() => void load());

    return () => {
      isMounted.current = false;
    };
  }, [load]);

  return { manifest, status, error, refresh: load };
}
