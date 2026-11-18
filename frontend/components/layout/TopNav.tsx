import Image from "next/image";
import { MenuIcon, PanelRightIcon } from "@/components/ui/icons";
import { SearchBar } from "@/components/ui/SearchBar";

// Placeholder-only per the locked spec — these become real routes once the
// corresponding feature (Anatomy Explorer, Quiz System, Bookmarks) is built.
const NAV_ITEMS = ["Learn", "Quiz", "Bookmarks"];

interface TopNavProps {
  onToggleSidebar: () => void;
  onToggleInfoPanel: () => void;
}

export function TopNav({ onToggleSidebar, onToggleInfoPanel }: TopNavProps) {
  return (
    <header className="border-line bg-panel flex h-14 flex-none items-center gap-3 border-b px-4">
      <button
        type="button"
        onClick={onToggleSidebar}
        className="rounded-control text-ink-muted hover:bg-panel-elevated hover:text-ink p-1.5 lg:hidden"
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
          className="rounded-control size-7 object-cover"
        />
        <span className="text-ink hidden text-sm font-semibold tracking-tight sm:inline">
          AnatoVision
        </span>
      </div>

      <nav aria-label="Primary" className="hidden flex-none items-center gap-1 md:flex">
        {NAV_ITEMS.map((item) => (
          <span
            key={item}
            aria-disabled="true"
            title="Available in a later phase"
            className="rounded-control text-ink-subtle cursor-default px-3 py-1.5 text-sm"
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
        <button
          type="button"
          onClick={onToggleInfoPanel}
          className="rounded-control text-ink-muted hover:bg-panel-elevated hover:text-ink p-1.5 xl:hidden"
          aria-label="Toggle information panel"
        >
          <PanelRightIcon />
        </button>
      </div>
    </header>
  );
}
