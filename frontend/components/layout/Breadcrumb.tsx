import Link from "next/link";
import { ChevronRightIcon } from "@/components/ui/icons";

interface BreadcrumbProps {
  systemName?: string | null;
  structureName?: string | null;
  onClearStructure?: () => void;
}

/** Body Systems → System → Structure, matching whatever's selected. */
export function Breadcrumb({ systemName, structureName, onClearStructure }: BreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" className="flex flex-none items-center gap-1 px-3 pt-2.5 text-xs">
      <Link
        href="/"
        className="rounded-control px-1.5 py-1 text-ink-subtle transition-colors hover:text-ink"
      >
        Body Systems
      </Link>

      {systemName && (
        <>
          <ChevronRightIcon width={12} height={12} className="flex-none text-ink-subtle" />
          {structureName ? (
            <button
              type="button"
              onClick={onClearStructure}
              className="rounded-control px-1.5 py-1 text-ink-subtle transition-colors hover:text-ink"
            >
              {systemName}
            </button>
          ) : (
            <span aria-current="page" className="rounded-control px-1.5 py-1 text-ink">
              {systemName}
            </span>
          )}
        </>
      )}

      {structureName && (
        <>
          <ChevronRightIcon width={12} height={12} className="flex-none text-ink-subtle" />
          <span aria-current="page" className="rounded-control px-1.5 py-1 text-ink">
            {structureName}
          </span>
        </>
      )}
    </nav>
  );
}
