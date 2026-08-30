"use client";

import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { SearchIcon } from "@/components/ui/icons";
import { searchAnatomy, type AnatomySearchResult } from "@/lib/data/anatomy";

interface SearchBarProps {
  placeholder?: string;
  className?: string;
}

/** Instant client-side search across body systems and key structures.
 * Selecting a result navigates to that structure's parent system page. */
export function SearchBar({
  placeholder = "Search systems or structures…",
  className = "",
}: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const listboxId = useId();
  const router = useRouter();

  // Derived directly from `query` — no effect needed for filtering.
  const results = useMemo(() => searchAnatomy(query), [query]);

  // Reset the highlighted index whenever the query changes. Adjusted during
  // render (React's recommended pattern) rather than in an effect, which
  // would call setState synchronously in the effect body.
  const [prevQuery, setPrevQuery] = useState(query);
  const [highlighted, setHighlighted] = useState(0);
  if (query !== prevQuery) {
    setPrevQuery(query);
    setHighlighted(0);
  }

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function selectResult(result: AnatomySearchResult) {
    // Structure results resolve through the same ?structure= mechanism
    // AppShell/RightInspector use — one selection path, not a second one.
    const target =
      result.type === "structure"
        ? `/anatomy/${result.systemId}?structure=${result.id}`
        : `/anatomy/${result.systemId}`;
    router.push(target);
    setQuery(""); // clearing query also clears the derived `results`
    setIsOpen(false);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!isOpen || results.length === 0) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlighted((i) => (i + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlighted((i) => (i - 1 + results.length) % results.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      const chosen = results[highlighted];
      if (chosen) selectResult(chosen);
    } else if (event.key === "Escape") {
      setIsOpen(false);
    }
  }

  const showDropdown = isOpen && query.trim().length > 0;

  return (
    <div ref={containerRef} className={`relative w-full ${className}`}>
      <label className="relative block w-full">
        <span className="sr-only">Search anatomy topics</span>
        <SearchIcon
          className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-ink-subtle"
          width={15}
          height={15}
        />
        <input
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          role="combobox"
          aria-expanded={showDropdown}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={
            showDropdown && results[highlighted] ? `${listboxId}-${highlighted}` : undefined
          }
          className="w-full rounded-control border border-line bg-background py-1.5 pr-3 pl-9 text-sm text-ink placeholder:text-ink-subtle focus-visible:border-accent"
        />
      </label>

      {showDropdown && (
        <ul
          id={listboxId}
          role="listbox"
          aria-label="Search results"
          className="scroll-thin absolute top-full z-40 mt-1.5 max-h-72 w-full overflow-y-auto rounded-panel border border-line bg-panel-elevated p-1 shadow-sm"
        >
          {results.length === 0 ? (
            <li className="px-3 py-2 text-xs text-ink-subtle">
              No matches for &ldquo;{query}&rdquo;
            </li>
          ) : (
            results.map((result, index) => (
              <li
                key={`${result.type}-${result.id}`}
                id={`${listboxId}-${index}`}
                role="option"
                aria-selected={index === highlighted}
              >
                <button
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => selectResult(result)}
                  onMouseEnter={() => setHighlighted(index)}
                  className={`flex w-full items-center justify-between gap-2 rounded-control px-2.5 py-2 text-left text-sm transition-colors ${
                    index === highlighted
                      ? "bg-accent-soft text-accent"
                      : "text-ink-muted hover:bg-panel"
                  }`}
                >
                  <span>{result.label}</span>
                  {result.sublabel && (
                    <span className="flex-none text-xs text-ink-subtle">{result.sublabel}</span>
                  )}
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
