import type { useApiStatus } from "@/hooks/useApiStatus";
import { StatusDot } from "@/components/ui/StatusDot";

const LABEL: Record<string, string> = {
  checking: "Checking…",
  online: "Online",
  offline: "Offline",
};

interface ConnectionBadgeProps {
  result: ReturnType<typeof useApiStatus>;
}

/** Compact, always-visible sibling of <ConnectionStatus /> for the top nav. */
export function ConnectionBadge({ result }: ConnectionBadgeProps) {
  return (
    <div className="flex items-center gap-2 rounded-control border border-line bg-panel px-2.5 py-1.5">
      <StatusDot state={result.state} />
      <span className="text-xs text-ink-muted">{LABEL[result.state]}</span>
    </div>
  );
}
