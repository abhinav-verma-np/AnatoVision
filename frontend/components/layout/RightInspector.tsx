"use client";

import Link from "next/link";
import { useManifest } from "@/hooks/useManifest";
import { getSystemById, type AnatomySystem, type KeyStructure } from "@/lib/data/anatomy";
import { resolveModel } from "@/lib/modelResolver";
import { useBookmarks } from "@/lib/bookmarks";
import { SectionCard } from "@/components/ui/SectionCard";
import { StarIcon } from "@/components/ui/icons";

interface RightInspectorProps {
  open: boolean;
  onClose: () => void;
  system: AnatomySystem | null;
  selectedStructure: KeyStructure | null;
  onSelectStructure: (structure: KeyStructure) => void;
}

/** Right information panel — stacked SectionCards, dynamic per selected
 * body system and structure. Model availability is resolved through the
 * shared manifest hook rather than duplicated here. */
export function RightInspector({
  open,
  onClose,
  system,
  selectedStructure,
  onSelectStructure,
}: RightInspectorProps) {
  const { isBookmarked, toggleBookmark } = useBookmarks();
  const { manifest } = useManifest();
  const bookmarked = system ? isBookmarked(system.id) : false;

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
        className={`scroll-thin border-line bg-panel fixed inset-y-0 right-0 z-30 w-80 flex-none overflow-y-auto border-l transition-transform duration-200 ease-out xl:static xl:z-auto xl:translate-x-0 ${
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
                    bookmarked
                      ? `Remove ${system.name} bookmark`
                      : `Bookmark ${system.name}`
                  }
                  title={bookmarked ? "Remove bookmark" : "Bookmark this system"}
                  className="rounded-control text-ink-subtle hover:text-accent p-1 transition-colors"
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
                  <dd className="text-ink mt-0.5">{selectedStructure.name}</dd>
                </div>
                <div>
                  <dt className="text-ink-subtle">System</dt>
                  <dd className="text-ink-muted mt-0.5">{system.name}</dd>
                </div>
              </dl>
            </SectionCard>
          )}

          <SectionCard title="Quick Facts">
            {system ? (
              <dl className="grid grid-cols-2 gap-x-3 gap-y-2 font-mono text-xs">
                {system.quickFacts.map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-ink-subtle">{label}</dt>
                    <dd className="text-ink-muted mt-0.5">{value}</dd>
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
                  const hasModel = manifest
                    ? resolveModel(manifest, structure)?.available
                    : undefined;
                  return (
                    <li key={structure.id}>
                      <button
                        type="button"
                        onClick={() => onSelectStructure(structure)}
                        aria-pressed={isActive}
                        className={`rounded-control w-full border px-2.5 py-2 text-left text-xs transition-colors ${
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
                            <span className="text-ink-subtle flex-none text-[10px]">
                              3D
                            </span>
                          )}
                        </span>
                        <span className="text-ink-subtle mt-0.5 block">
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
                        className="rounded-control border-line text-ink-muted hover:border-line-strong hover:text-ink border px-2 py-1 text-xs transition-colors"
                      >
                        {related.shortName}
                      </Link>
                    );
                  })}
                </div>
                <p className="text-ink-subtle text-xs">
                  Flashcards and quizzes for the {system.shortName} System arrive in a
                  later phase.
                </p>
              </div>
            ) : (
              <p>
                Related systems and study resources appear here once a system is selected.
              </p>
            )}
          </SectionCard>
        </div>
      </aside>
    </>
  );
}
