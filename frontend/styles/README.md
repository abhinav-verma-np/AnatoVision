# `styles/`

Reserved for modular stylesheets beyond the global theme.

The current global theme (colors, fonts, radii) lives in
`app/globals.css` as Tailwind v4 CSS-first tokens — that's the single
source of truth for the locked design system. This folder is for
anything that shouldn't live in that one file as the app grows, e.g.
print stylesheets or viewer-specific CSS that Tailwind utilities alone
don't cover well (such as Cornerstone.js/vtk.js canvas overlays in a
later phase).

Empty for now, by design — nothing in Phase 1 needs it yet.
