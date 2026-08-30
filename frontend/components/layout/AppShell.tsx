"use client";

import { useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useApiStatus } from "@/hooks/useApiStatus";
import { getSystemById, type KeyStructure } from "@/lib/data/anatomy";
import { TopNav } from "@/components/layout/TopNav";
import { Sidebar } from "@/components/layout/Sidebar";
import { ViewerWorkspace } from "@/components/layout/ViewerWorkspace";
import { RightInspector } from "@/components/layout/RightInspector";

/**
 * The locked three-column shell: top nav, left sidebar, central viewer
 * workspace, right info panel. Sidebar and info panel collapse into
 * off-canvas drawers below the lg / xl breakpoints — same structure, no
 * alternate layout, per the UI-lock rules in the project constitution.
 *
 * Selected body system comes from the URL path (`/anatomy/[system]`) via
 * useParams; selected structure comes from a `?structure=` query param
 * rather than local component state. Two reasons: (1) switching systems
 * via the sidebar naturally drops any lingering structure param — no
 * manual "reset on change" logic needed — and (2) it gives Search a
 * single, uniform way to jump straight to a structure (system + structure
 * in one navigation) without a second selection mechanism.
 *
 * One useApiStatus() poll lives here and is shared by the nav's
 * ConnectionBadge. Manifest loading is NOT lifted here — useManifest()
 * caches at module scope, so ViewerWorkspace/RightInspector/SearchBar
 * each calling it independently costs one network request total, not one
 * per component.
 */
export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [infoPanelOpen, setInfoPanelOpen] = useState(false);
  const apiStatus = useApiStatus();
  const router = useRouter();

  const params = useParams<{ system?: string }>();
  const searchParams = useSearchParams();

  const systemId = typeof params.system === "string" ? params.system : undefined;
  const system = systemId ? (getSystemById(systemId) ?? null) : null;

  const structureId = searchParams.get("structure");
  const selectedStructure: KeyStructure | null =
    (system && structureId && system.keyStructures.find((s) => s.id === structureId)) || null;

  function handleSelectStructure(structure: KeyStructure) {
    if (!systemId) return;
    router.push(`/anatomy/${systemId}?structure=${structure.id}`);
  }

  function handleClearStructure() {
    if (!systemId) return;
    router.replace(`/anatomy/${systemId}`);
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TopNav
        apiStatus={apiStatus}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
        onToggleInfoPanel={() => setInfoPanelOpen((v) => !v)}
      />

      <div className="flex min-h-0 flex-1">
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <ViewerWorkspace
          system={system}
          structure={selectedStructure}
          onClearStructure={handleClearStructure}
        />
        <RightInspector
          open={infoPanelOpen}
          onClose={() => setInfoPanelOpen(false)}
          apiStatus={apiStatus}
          system={system}
          selectedStructure={selectedStructure}
          onSelectStructure={handleSelectStructure}
        />
      </div>
    </div>
  );
}
