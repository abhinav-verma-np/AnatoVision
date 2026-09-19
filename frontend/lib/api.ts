/**
 * Thin fetch wrapper shared by every service module.
 *
 * Centralizing this now means Phase 2+ features (anatomy data, quiz
 * progress sync, etc.) get consistent timeout handling and error shapes
 * for free instead of every feature reinventing fetch().
 */

const DEFAULT_TIMEOUT_MS = 5000;
const PRODUCTION_API_URL = "https://anatovision.onrender.com";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ??
  (process.env.NODE_ENV === "production" ? PRODUCTION_API_URL : "http://localhost:8000");

export class ApiError extends Error {
  constructor(
    message: string,
    public override readonly cause?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface ApiFetchOptions extends RequestInit {
  timeoutMs?: number;
}

/**
 * Calls the AnatoVision backend and returns parsed JSON.
 * Throws ApiError for network failures, timeouts, and non-2xx responses —
 * callers decide how to surface that (e.g. an "offline" badge), this
 * function only normalizes failure into one shape.
 */
export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...init } = options;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...init.headers,
      },
    });

    if (!response.ok) {
      throw new ApiError(`Backend responded with status ${response.status}`);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request to backend timed out", error);
    }
    throw new ApiError("Could not reach the backend", error);
  } finally {
    clearTimeout(timeout);
  }
}
