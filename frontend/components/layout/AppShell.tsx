"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useApiStatus } from "@/hooks/useApiStatus";
import { getSystemById } from "@/lib/data/anatomy";
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
 * Selected body system comes from the URL (`/anatomy/[system]`) via
 * useParams, so this same component works for both `/` (no system) and
 * every `/anatomy/*` route without prop drilling from two different
 * page.tsx files. Selected structure is local UI state, cleared whenever
 * the system changes.
 */
export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [infoPanelOpen, setInfoPanelOpen] = useState(false);
  const [selectedStructure, setSelectedStructure] = useState<string | null>(null);
  const apiStatus = useApiStatus();

  const params = useParams<{ system?: string }>();
  const systemId = typeof params.system === "string" ? params.system : undefined;
  const system = systemId ? (getSystemById(systemId) ?? null) : null;

  // Clear the selected structure whenever the system changes. Adjusted
  // during render (React's recommended pattern for "reset state when a
  // prop changes") rather than in an effect, which would call setState
  // synchronously in the effect body.
  const [prevSystemId, setPrevSystemId] = useState(systemId);
  if (systemId !== prevSystemId) {
    setPrevSystemId(systemId);
    setSelectedStructure(null);
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
          structureName={selectedStructure}
          onClearStructure={() => setSelectedStructure(null)}
        />
        <RightInspector
          open={infoPanelOpen}
          onClose={() => setInfoPanelOpen(false)}
          apiStatus={apiStatus}
          system={system}
          onSelectStructure={setSelectedStructure}
        />
      </div>
    </div>
  );
}
