"use client";

import { useState } from "react";
import type { AnatomySystem } from "@/lib/data/anatomy";
import { WorkspaceHeader } from "@/components/layout/WorkspaceHeader";
import { StatusBar } from "@/components/layout/StatusBar";
import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { AnatomyIllustration } from "@/components/ui/AnatomyIllustration";

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
  structureName?: string | null;
  onClearStructure?: () => void;
}

/** Central viewer area: breadcrumb, tab strip, viewer canvas placeholder,
 * bottom status bar. Content is system-aware but no real viewer is
 * implemented — 3D/X-ray/CT/MRI/Ultrasound/PET rendering belongs to a
 * later phase. */
export function ViewerWorkspace({ system, structureName, onClearStructure }: ViewerWorkspaceProps) {
  const [activeTab, setActiveTab] = useState(VIEWER_TABS[0]!);

  const title = system ? system.name : "Anatomy Explorer";
  const subtitle = system
    ? `${activeTab} preview — select an imaging modality above`
    : "Select a body system from the sidebar to begin";

  const showSystemPreview = system !== null && activeTab === "3D Anatomy";

  return (
    <main className="scroll-thin flex min-w-0 flex-1 flex-col overflow-y-auto bg-background p-4">
      <div className="flex min-h-0 flex-1 flex-col rounded-panel border border-line bg-panel shadow-sm">
        <Breadcrumb
          systemName={system?.name}
          structureName={structureName}
          onClearStructure={onClearStructure}
        />

        <WorkspaceHeader
          tabs={VIEWER_TABS}
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          title={title}
          subtitle={subtitle}
        />

        <div className="flex flex-1 items-center justify-center p-8">
          {showSystemPreview && system ? (
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

        <StatusBar />
      </div>
    </main>
  );
}
