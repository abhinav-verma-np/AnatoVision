import type { useApiStatus } from "@/hooks/useApiStatus";
import Image from "next/image";
import { MenuIcon, PanelRightIcon, UserIcon } from "@/components/ui/icons";
import { SearchBar } from "@/components/ui/SearchBar";
import { ConnectionBadge } from "@/features/connection-status/ConnectionBadge";

// Placeholder-only per the locked spec — these become real routes once the
// corresponding feature (Anatomy Explorer, Quiz System, Bookmarks) is built.
const NAV_ITEMS = ["Learn", "Quiz", "Bookmarks"];

interface TopNavProps {
  apiStatus: ReturnType<typeof useApiStatus>;
  onToggleSidebar: () => void;
  onToggleInfoPanel: () => void;
}

export function TopNav({ apiStatus, onToggleSidebar, onToggleInfoPanel }: TopNavProps) {
  return (
    <header className="flex h-14 flex-none items-center gap-3 border-b border-line bg-panel px-4">
      <button
        type="button"
        onClick={onToggleSidebar}
        className="rounded-control p-1.5 text-ink-muted hover:bg-panel-elevated hover:text-ink lg:hidden"
        aria-label="Toggle body systems sidebar"
      >
        <MenuIcon />
      </button>

      {/* Logo */}
      <div className="flex flex-none items-center gap-2">
        <Image
          src="https://img.abhinavverma.com.np/anstovision-logo.png"
          alt="AnatoVision"
          width={28}
          height={28}
          unoptimized
          className="size-7 rounded-control object-cover"
        />
        <span className="hidden text-sm font-semibold tracking-tight text-ink sm:inline">
          AnatoVision
        </span>
      </div>

      <nav aria-label="Primary" className="hidden flex-none items-center gap-1 md:flex">
        {NAV_ITEMS.map((item) => (
          <span
            key={item}
            aria-disabled="true"
            title="Available in a later phase"
            className="cursor-default rounded-control px-3 py-1.5 text-sm text-ink-subtle"
          >
            {item}
          </span>
        ))}
      </nav>

      {/* Centered search */}
      <div className="mx-auto hidden w-full max-w-md sm:block">
        <SearchBar />
      </div>

      <div className="ml-auto flex flex-none items-center gap-3">
        <ConnectionBadge result={apiStatus} />

        <button
          type="button"
          aria-disabled="true"
          title="Profile & settings — available in a later phase"
          className="flex size-8 flex-none cursor-default items-center justify-center rounded-full border border-line text-ink-subtle hover:bg-panel-elevated"
        >
          <UserIcon width={16} height={16} />
        </button>

        <button
          type="button"
          onClick={onToggleInfoPanel}
          className="rounded-control p-1.5 text-ink-muted hover:bg-panel-elevated hover:text-ink xl:hidden"
          aria-label="Toggle information panel"
        >
          <PanelRightIcon />
        </button>
      </div>
    </header>
  );
}
