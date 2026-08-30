interface WorkspaceHeaderProps {
  tabs: string[];
  activeTab: string;
  onSelectTab: (tab: string) => void;
  title?: string;
  subtitle?: string;
}

/** Viewer-type tab strip, with an optional title row above it that updates
 * with the selected body system. Switching tabs only changes which
 * placeholder is shown — no viewer rendering is implemented yet. */
export function WorkspaceHeader({
  tabs,
  activeTab,
  onSelectTab,
  title,
  subtitle,
}: WorkspaceHeaderProps) {
  return (
    <div className="flex-none border-b border-line">
      {title && (
        <div className="px-3 pt-2 pb-1">
          <h1 className="text-sm font-semibold text-ink">{title}</h1>
          {subtitle && <p className="mt-0.5 text-xs text-ink-subtle">{subtitle}</p>}
        </div>
      )}

      <div
        role="tablist"
        aria-label="Viewer type"
        className="scroll-thin flex items-center gap-1 overflow-x-auto px-3 py-2"
      >
        {tabs.map((tab) => {
          const isActive = tab === activeTab;
          return (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => onSelectTab(tab)}
              className={`flex-none rounded-control px-3 py-1.5 text-xs font-medium transition-colors ${
                isActive
                  ? "bg-accent-soft text-accent"
                  : "text-ink-subtle hover:bg-panel-elevated hover:text-ink-muted"
              }`}
            >
              {tab}
            </button>
          );
        })}
      </div>
    </div>
  );
}
