import type { ConnectionState } from "@/hooks/useApiStatus";

const COLOR_BY_STATE: Record<ConnectionState, string> = {
  online: "bg-success",
  offline: "bg-danger",
  checking: "bg-ink-subtle",
};

const PULSE_BY_STATE: Record<ConnectionState, string> = {
  online: "",
  offline: "",
  checking: "animate-pulse",
};

export function StatusDot({ state }: { state: ConnectionState }) {
  return (
    <span
      className={`inline-block size-2 rounded-full ${COLOR_BY_STATE[state]} ${PULSE_BY_STATE[state]}`}
      aria-hidden="true"
    />
  );
}
