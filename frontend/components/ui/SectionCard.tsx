interface SectionCardProps {
  title: string;
  badge?: string;
  /** Custom right-side slot (e.g. a bookmark toggle). Takes precedence over `badge`. */
  action?: React.ReactNode;
  children: React.ReactNode;
}

/** Locked-design panel wrapper: rounded-panel, thin border, soft elevation. */
export function SectionCard({ title, badge, action, children }: SectionCardProps) {
  return (
    <section className="rounded-panel border border-line bg-panel-elevated p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-xs font-medium tracking-wide text-ink-subtle uppercase">{title}</h2>
        {action ??
          (badge && (
            <span className="rounded-control border border-line px-1.5 py-0.5 text-[10px] text-ink-subtle">
              {badge}
            </span>
          ))}
      </div>
      <div className="mt-2.5 text-sm text-ink-muted">{children}</div>
    </section>
  );
}
