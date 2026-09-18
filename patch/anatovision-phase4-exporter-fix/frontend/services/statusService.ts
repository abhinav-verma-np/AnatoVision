import { apiFetch } from "@/lib/api";

/**
 * Mirrors backend/app/schemas/status.py — keep these two in sync.
 */
export interface ApiStatusResponse {
  status: string;
  service: string;
  environment: string;
  version: string;
  timestamp: string;
}

export function getApiStatus(): Promise<ApiStatusResponse> {
  return apiFetch<ApiStatusResponse>("/api/status");
}
