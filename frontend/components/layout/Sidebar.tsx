"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronsLeftIcon, StarIcon } from "@/components/ui/icons";
import { ANATOMY_SYSTEMS } from "@/lib/data/anatomy";
import { useBookmarks } from "@/lib/bookmarks";

// Imaging modalities stay inert placeholders — viewers ship in a later phase.
const MODALITIES = ["X-Ray", "CT", "MRI", "Ultrasound", "PET/SPECT"];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
const [mounted, setMounted] = useState(false);

useEffect(() => {
  queueMicrotask(() => setMounted(true));
}, []);

const pathname = usePathname();
const { isBookmarked } = useBookmarks();

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <button
          type="button"
          aria-label="Close sidebar"
          onClick={onClose}
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
        />
      )}

      <aside
        className={`scroll-thin fixed inset-y-0 left-0 z-30 flex-none overflow-y-auto border-r border-line bg-panel transition-[width,transform] duration-200 ease-out lg:static lg:z-auto lg:translate-x-0 ${
          collapsed ? "lg:w-16" : "lg:w-64"
        } w-64 ${open ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="flex flex-col p-4">
          <button
            type="button"
            onClick={() => setCollapsed((v) => !v)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed}
            className={`mb-3 hidden items-center gap-1.5 self-end rounded-control p-1.5 text-ink-subtle hover:bg-panel-elevated hover:text-ink lg:flex ${
              collapsed ? "self-center" : ""
            }`}
          >
            <ChevronsLeftIcon
              width={14}
              height={14}
              className={`transition-transform duration-200 ${collapsed ? "rotate-180" : ""}`}
            />
          </button>

          <div className="space-y-5">
            {/* Body Systems — interactive, routes to /anatomy/[system] */}
            <div>
              {!collapsed && (
                <h2 className="px-2 text-xs font-medium tracking-wide text-ink-subtle uppercase">
                  Body Systems
                </h2>
              )}
              <ul
                className={`mt-2 space-y-0.5 ${collapsed ? "flex flex-col items-center gap-1" : ""}`}
              >
                {ANATOMY_SYSTEMS.map((system) => {
                  const href = `/anatomy/${system.id}`;
                  const isActive = pathname === href;
                  const bookmarked = mounted && isBookmarked(system.id);

                  return (
                    <li key={system.id} className={collapsed ? "" : "w-full"}>
                      <Link
                        href={href}
                        onClick={onClose}
                        aria-current={isActive ? "page" : undefined}
                        title={system.name}
                        className={
                          collapsed
                            ? `flex size-9 items-center justify-center rounded-control border font-mono text-[10px] transition-colors ${
                                isActive
                                  ? "border-accent bg-accent-soft text-accent"
                                  : "border-line text-ink-muted hover:bg-panel-elevated"
                              }`
                            : `flex items-center justify-between gap-2 rounded-control px-2.5 py-2 text-sm transition-colors ${
                                isActive
                                  ? "bg-accent-soft text-accent"
                                  : "text-ink-muted hover:bg-panel-elevated"
                              }`
                        }
                      >
                        {collapsed ? (
                          system.shortName.slice(0, 2).toUpperCase()
                        ) : (
                          <>
                            <span>{system.shortName}</span>
                            {bookmarked && (
                              <StarIcon
                                width={12}
                                height={12}
                                filled
                                aria-hidden="true"
                                className="flex-none text-accent"
                              />
                            )}
                          </>
                        )}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>

            {/* Imaging Modalities — placeholder only, per Phase 3 restrictions */}
            <div>
              {!collapsed && (
                <h2 className="px-2 text-xs font-medium tracking-wide text-ink-subtle uppercase">
                  Imaging Modalities
                </h2>
              )}
              <ul
                className={`mt-2 space-y-0.5 ${collapsed ? "flex flex-col items-center gap-1" : ""}`}
              >
                {MODALITIES.map((item) => (
                  <li key={item} className={collapsed ? "" : "w-full"}>
                    <span
                      aria-disabled="true"
                      title={`${item} — available in a later phase`}
                      className={
                        collapsed
                          ? "flex size-9 cursor-default items-center justify-center rounded-control border border-line font-mono text-[10px] text-ink-muted hover:bg-panel-elevated"
                          : "block cursor-default rounded-control px-2.5 py-2 text-sm text-ink-muted hover:bg-panel-elevated"
                      }
                    >
                      {collapsed ? item.slice(0, 2).toUpperCase() : item}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {!collapsed && (
            <div className="mt-4 rounded-panel border border-dashed border-line px-3 py-3">
              <p className="text-xs text-ink-subtle">
                Select a body system to explore key structures, quick facts, and imaging
                availability.
              </p>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
