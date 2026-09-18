import { ChevronLeftIcon, ChevronRightIcon, ResetIcon, ZoomInIcon, ZoomOutIcon } from "@/components/ui/icons";

/** Bottom workspace bar — slice navigation, timeline, and viewer controls.
 * All inert; wired up alongside the imaging viewers in a later phase. */
export function StatusBar() {
  return (
    <div className="flex flex-none flex-wrap items-center gap-x-6 gap-y-2 rounded-b-panel border-t border-line px-3 py-2">
      {/* Slice navigation */}
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          disabled
          aria-label="Previous slice"
          className="rounded-control p-1 text-ink-subtle disabled:cursor-not-allowed"
        >
          <ChevronLeftIcon width={14} height={14} />
        </button>
        <span className="font-mono text-[11px] text-ink-subtle">Slice — / —</span>
        <button
          type="button"
          disabled
          aria-label="Next slice"
          className="rounded-control p-1 text-ink-subtle disabled:cursor-not-allowed"
        >
          <ChevronRightIcon width={14} height={14} />
        </button>
      </div>

      {/* Timeline */}
      <div className="flex min-w-[120px] flex-1 items-center gap-2">
        <input
          type="range"
          disabled
          aria-label="Timeline"
          className="w-full accent-accent disabled:cursor-not-allowed"
        />
        <span className="flex-none font-mono text-[11px] text-ink-subtle">00:00 / 00:00</span>
      </div>

      {/* Viewer controls */}
      <div className="flex items-center gap-1">
        <button
          type="button"
          disabled
          aria-label="Zoom out"
          className="rounded-control p-1 text-ink-subtle disabled:cursor-not-allowed"
        >
          <ZoomOutIcon width={14} height={14} />
        </button>
        <span className="w-9 text-center font-mono text-[11px] text-ink-subtle">100%</span>
        <button
          type="button"
          disabled
          aria-label="Zoom in"
          className="rounded-control p-1 text-ink-subtle disabled:cursor-not-allowed"
        >
          <ZoomInIcon width={14} height={14} />
        </button>
        <button
          type="button"
          disabled
          aria-label="Reset view"
          className="ml-1 rounded-control p-1 text-ink-subtle disabled:cursor-not-allowed"
        >
          <ResetIcon width={14} height={14} />
        </button>
      </div>
    </div>
  );
}
