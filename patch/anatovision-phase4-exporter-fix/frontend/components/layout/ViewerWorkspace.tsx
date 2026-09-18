"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import type { AnatomySystem, KeyStructure } from "@/lib/data/anatomy";
import { resolveModel } from "@/lib/modelResolver";
import { useManifest } from "@/hooks/useManifest";
import { WorkspaceHeader } from "@/components/layout/WorkspaceHeader";
import { StatusBar } from "@/components/layout/StatusBar";
import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { AnatomyIllustration } from "@/components/ui/AnatomyIllustration";
import { CubeIcon } from "@/components/ui/icons";

// three.js/R3F/drei (~900KB) only enters the browser bundle when a 3D
// model actually needs to render, not on every page load — most visits
// (browsing systems, reading facts) never download it at all.
const ModelViewer = dynamic(
  () => import("@/features/anatomy-viewer/ModelViewer").then((mod) => mod.ModelViewer),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full flex-col items-center justify-center gap-2">
        <span className="size-2 animate-pulse rounded-full bg-accent" aria-hidden="true" />
        <p className="text-xs text-ink-subtle">Loading viewer…</p>
      </div>
    ),
  },
);

const VIEWER_TABS = ["3D Anatomy", "X-Ray", "CT", "MRI", "Ultrasound", "PET/SPECT"];

const GENERIC_VIEWER_COPY: Record<string, string> = {
  "3D Anatomy":
    "The 3D Anatomy Viewer will render an interactive, rotatable model of the selected structure.",
  "X-Ray": "The X-Ray Viewer will render radiographic images for the selected structure.",
  CT: "The CT Viewer will render cross-sectional CT slices for the selected structure.",
  MRI: "The MRI Viewer will render MRI sequences for the selected structure.",
  Ultrasound: "The Ultrasound Viewer will render sonographic images for the selected structure.",
  "PET/SPECT": "The PET/SPECT Viewer will render functional imaging for the selected structure.",
};

interface ViewerWorkspaceProps {
  system: AnatomySystem | null;
  structure: KeyStructure | null;
  onClearStructure?: () => void;
}

/** Central viewer area: breadcrumb, tab strip, viewer canvas, bottom
 * status bar. On the "3D Anatomy" tab with a structure selected, renders
 * the real GLB model (resolved through the manifest) instead of a
 * placeholder — every other tab/state stays a placeholder, per the
 * project constitution (no X-ray/CT/MRI/Ultrasound/PET viewer yet). */
export function ViewerWorkspace({ system, structure, onClearStructure }: ViewerWorkspaceProps) {
  const [activeTab, setActiveTab] = useState(VIEWER_TABS[0]!);
  const { manifest, status: manifestStatus } = useManifest();

  const title = system ? system.name : "Anatomy Explorer";
  const subtitle = structure
    ? `${structure.name} — ${activeTab}`
    : system
      ? `${activeTab} preview — select an imaging modality above`
      : "Select a body system from the sidebar to begin";

  const isThreeDTab = activeTab === "3D Anatomy";
  const resolvedModel =
    structure && manifest ? resolveModel(manifest, structure) : undefined;
  const modelIsAvailable = resolvedModel?.available === true;

  return (
    <main className="scroll-thin flex min-w-0 flex-1 flex-col overflow-y-auto bg-background p-4">
      <div className="flex min-h-0 flex-1 flex-col rounded-panel border border-line bg-panel shadow-sm">
        <Breadcrumb
          systemName={system?.name}
          structureName={structure?.name}
          onClearStructure={onClearStructure}
        />

        <WorkspaceHeader
          tabs={VIEWER_TABS}
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          title={title}
          subtitle={subtitle}
        />

        {isThreeDTab && structure ? (
          <div className="relative flex-1">
            {manifestStatus === "loading" ? (
              <div className="flex h-full flex-col items-center justify-center gap-2">
                <span className="size-2 animate-pulse rounded-full bg-accent" aria-hidden="true" />
                <p className="text-xs text-ink-subtle">Loading model catalog…</p>
              </div>
            ) : manifestStatus === "error" ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
                <p className="text-sm text-ink">Couldn&apos;t load the model catalog</p>
                <p className="max-w-xs text-xs text-ink-subtle">
                  manifest.json may be missing or malformed. Try refreshing the page.
                </p>
              </div>
            ) : modelIsAvailable && resolvedModel ? (
              <ModelViewer path={resolvedModel.path} label={structure.name} />
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
                <div className="flex size-12 items-center justify-center rounded-panel border border-line-strong text-ink-subtle">
                  <CubeIcon width={20} height={20} />
                </div>
                <h2 className="text-sm font-medium text-ink">{structure.name}</h2>
                <p className="max-w-sm text-sm text-ink-muted">
                  No 3D model is available for this structure yet. Run the Z-Anatomy export
                  pipeline to generate it.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-1 items-center justify-center p-8">
            {isThreeDTab && system ? (
              <div className="max-w-md text-center">
                <div className="mx-auto mb-4 flex size-28 items-center justify-center rounded-panel border border-line-strong text-accent">
                  <AnatomyIllustration systemId={system.id} />
                </div>
                <h2 className="text-sm font-medium text-ink">{system.name} Preview</h2>
                <p className="mt-1.5 text-sm text-ink-muted">{system.description}</p>
                <div className="mt-4 flex flex-wrap justify-center gap-1.5">
                  {system.imagingAvailability.map((modality) => (
                    <span
                      key={modality}
                      className="rounded-control border border-line px-2 py-1 font-mono text-[11px] text-ink-subtle"
                    >
                      {modality}
                    </span>
                  ))}
                </div>
                <p className="mt-4 text-xs text-ink-subtle">
                  Select a key structure from the right panel to load its 3D model.
                </p>
              </div>
            ) : (
              <div className="max-w-md text-center">
                <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-panel border border-line-strong text-ink-subtle">
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <path d="M3 15l4.5-4.5a2 2 0 0 1 2.8 0L15 15" />
                    <circle cx="9" cy="9" r="1.5" />
                  </svg>
                </div>
                <h2 className="text-sm font-medium text-ink">{activeTab} Viewer</h2>
                <p className="mt-1.5 text-sm text-ink-muted">
                  {system
                    ? `${GENERIC_VIEWER_COPY[activeTab]} Scoped to the ${system.name}.`
                    : GENERIC_VIEWER_COPY[activeTab]}
                </p>
              </div>
            )}
          </div>
        )}

        <StatusBar />
      </div>
    </main>
  );
}
