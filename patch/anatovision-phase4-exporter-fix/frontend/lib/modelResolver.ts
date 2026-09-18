import type { KeyStructure } from "@/lib/data/anatomy";
import { GENERATED_MANIFEST_ALIASES } from "@/lib/data/generatedManifestAliases";
import { getModel, type Manifest, type ResolvedModel } from "@/lib/manifest";

/**
 * Resolves a structure to its manifest entry, trying in order:
 *   1. Exact id match (unchanged, fully backward compatible)
 *   2. Curated `structure.manifestAliases` (hand-confirmed, for cases
 *      needing human judgment — e.g. ambiguous automated candidates)
 *   3. `GENERATED_MANIFEST_ALIASES` (algorithmic, produced by
 *      scripts/generate-structure-aliases.ts — never hand-typed)
 *
 * Only ever returns an entry that's ACTUALLY present in the manifest —
 * an unmatched or unconfirmed structure returns undefined, which callers
 * treat as "no 3D model available yet". This never invents a path.
 */
export function resolveModel(manifest: Manifest, structure: KeyStructure): ResolvedModel | undefined {
  const direct = getModel(manifest, structure.id);
  if (direct) return direct;

  for (const alias of structure.manifestAliases ?? []) {
    const resolved = getModel(manifest, alias);
    if (resolved) return resolved;
  }

  for (const alias of GENERATED_MANIFEST_ALIASES[structure.id] ?? []) {
    const resolved = getModel(manifest, alias);
    if (resolved) return resolved;
  }

  return undefined;
}
