"use client";

import Link from "next/link";
import type { useApiStatus } from "@/hooks/useApiStatus";
import { useManifest } from "@/hooks/useManifest";
import { getSystemById, type AnatomySystem, type KeyStructure } from "@/lib/data/anatomy";
import { getModel } from "@/lib/manifest";
import { useBookmarks } from "@/lib/bookmarks";
import { SectionCard } from "@/components/ui/SectionCard";
import { StatusDot } from "@/components/ui/StatusDot";
import { RefreshIcon, StarIcon } from "@/components/ui/icons";

interface RightInspectorProps {
  open: boolean;
  onClose: () => void;
  apiStatus: ReturnType<typeof useApiStatus>;
  system: AnatomySystem | null;
  selectedStructure: KeyStructure | null;
  onSelectStructure: (structure: KeyStructure) => void;
}

const STATUS_LABEL: Record<string, string> = {
  checking: "Checking backend…",
  online: "Backend connected",
  offline: "Backend unreachable",
};

/** Right information panel — stacked SectionCards, dynamic per selected
 * body system and structure. System Status reuses the app-wide
 * useApiStatus() poll shared with TopNav's ConnectionBadge; model
 * availability is resolved through the shared manifest hook rather than
 * duplicated here. */
export function RightInspector({
  open,
  onClose,
  apiStatus,
  system,
  selectedStructure,
  onSelectStructure,
}: RightInspectorProps) {
  const { state, lastCheckedAt, refresh } = apiStatus;
  const { isBookmarked, toggleBookmark } = useBookmarks();
  const { manifest } = useManifest();
  const bookmarked = system ? isBookmarked(system.id) : false;

  const selectedModel =
    selectedStructure && manifest ? getModel(manifest, selectedStructure.id) : undefined;

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close information panel"
          onClick={onClose}
          className="fixed inset-0 z-20 bg-black/60 xl:hidden"
        />
      )}

      <aside
        className={`scroll-thin fixed inset-y-0 right-0 z-30 w-80 flex-none overflow-y-auto border-l border-line bg-panel transition-transform duration-200 ease-out xl:static xl:z-auto xl:translate-x-0 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="space-y-4 p-4">
          <SectionCard
            title="Anatomy Overview"
            action={
              system ? (
                <button
                  type="button"
                  onClick={() => toggleBookmark(system.id)}
                  aria-pressed={bookmarked}
                  aria-label={
                    bookmarked ? `Remove ${system.name} bookmark` : `Bookmark ${system.name}`
                  }
                  title={bookmarked ? "Remove bookmark" : "Bookmark this system"}
                  className="rounded-control p-1 text-ink-subtle transition-colors hover:text-accent"
                >
                  <StarIcon width={14} height={14} filled={bookmarked} />
                </button>
              ) : undefined
            }
          >
            {system ? (
              <p>{system.description}</p>
            ) : (
              <p>Select a body system from the sidebar to see its overview.</p>
            )}
          </SectionCard>

          {selectedStructure && system && (
            <SectionCard title="Selected Structure">
              <dl className="space-y-2 text-xs">
                <div>
                  <dt className="text-ink-subtle">Name</dt>
                  <dd className="mt-0.5 text-ink">{selectedStructure.name}</dd>
                </div>
                <div>
                  <dt className="text-ink-subtle">System</dt>
                  <dd className="mt-0.5 text-ink-muted">{system.name}</dd>
                </div>
                <div>
                  <dt className="text-ink-subtle">Availability</dt>
                  <dd className="mt-0.5">
                    {selectedModel?.available ? (
                      <span className="text-success">3D model available</span>
                    ) : (
                      <span className="text-ink-subtle">Not yet available</span>
                    )}
                  </dd>
                </div>
                {selectedModel?.available && (
                  <div>
                    <dt className="text-ink-subtle">Model path</dt>
                    <dd className="mt-0.5 truncate font-mono text-[11px] text-ink-subtle">
                      {selectedModel.path}
                    </dd>
                  </div>
                )}
              </dl>
            </SectionCard>
          )}

          <SectionCard title="Quick Facts">
            {system ? (
              <dl className="grid grid-cols-2 gap-x-3 gap-y-2 font-mono text-xs">
                {system.quickFacts.map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-ink-subtle">{label}</dt>
                    <dd className="mt-0.5 text-ink-muted">{value}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p>Quick facts appear here once a system is selected.</p>
            )}
          </SectionCard>

          <SectionCard title="Key Structures">
            {system ? (
              <ul className="space-y-1.5">
                {system.keyStructures.map((structure) => {
                  const isActive = selectedStructure?.id === structure.id;
                  const hasModel = manifest ? getModel(manifest, structure.id)?.available : undefined;
                  return (
                    <li key={structure.id}>
                      <button
                        type="button"
                        onClick={() => onSelectStructure(structure)}
                        aria-pressed={isActive}
                        className={`w-full rounded-control border px-2.5 py-2 text-left text-xs transition-colors ${
                          isActive
                            ? "border-accent bg-accent-soft"
                            : "border-line hover:border-line-strong"
                        }`}
                      >
                        <span className="flex items-center justify-between gap-2">
                          <span
                            className={`font-medium ${isActive ? "text-accent" : "text-ink"}`}
                          >
                            {structure.name}
                          </span>
                          {hasModel && (
                            <span className="flex-none text-[10px] text-ink-subtle">3D</span>
                          )}
                        </span>
                        <span className="mt-0.5 block text-ink-subtle">
                          {structure.description}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p>Key structures appear here once a system is selected.</p>
            )}
          </SectionCard>

          <SectionCard title="Related Learning">
            {system ? (
              <div className="space-y-2.5">
                <div className="flex flex-wrap gap-1.5">
                  {system.relatedSystemIds.map((id) => {
                    const related = getSystemById(id);
                    if (!related) return null;
                    return (
                      <Link
                        key={id}
                        href={`/anatomy/${related.id}`}
                        className="rounded-control border border-line px-2 py-1 text-xs text-ink-muted transition-colors hover:border-line-strong hover:text-ink"
                      >
                        {related.shortName}
                      </Link>
                    );
                  })}
                </div>
                <p className="text-xs text-ink-subtle">
                  Flashcards and quizzes for the {system.shortName} System arrive in a later
                  phase.
                </p>
              </div>
            ) : (
              <p>Related systems and study resources appear here once a system is selected.</p>
            )}
          </SectionCard>

          <SectionCard title="System Status">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <StatusDot state={state} />
                <span className="text-ink-muted">{STATUS_LABEL[state]}</span>
              </div>
              <button
                type="button"
                onClick={refresh}
                disabled={state === "checking"}
                aria-label="Recheck backend connection"
                title="Recheck backend connection"
                className="rounded-control p-1 text-ink-subtle transition-colors hover:text-ink disabled:opacity-40"
              >
                <RefreshIcon width={13} height={13} />
              </button>
            </div>
            <p className="mt-2 font-mono text-[11px] text-ink-subtle">
              Last checked: {lastCheckedAt ? lastCheckedAt.toLocaleTimeString() : "—"}
            </p>
          </SectionCard>
        </div>
      </aside>
    </>
  );
}
