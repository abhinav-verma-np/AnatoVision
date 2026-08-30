import { skeletal } from "./skeletal";
import { muscular } from "./muscular";
import { nervous } from "./nervous";
import { cardiovascular } from "./cardiovascular";
import { respiratory } from "./respiratory";
import { digestive } from "./digestive";
import { urinary } from "./urinary";
import { reproductive } from "./reproductive";
import type { AnatomySystem } from "./types";

export type { AnatomySystem, KeyStructure, ImagingModality } from "./types";

export const ANATOMY_SYSTEMS: AnatomySystem[] = [
  skeletal,
  muscular,
  nervous,
  cardiovascular,
  respiratory,
  digestive,
  urinary,
  reproductive,
];

const SYSTEM_BY_ID = new Map(ANATOMY_SYSTEMS.map((system) => [system.id, system]));

export function getSystemById(id: string): AnatomySystem | undefined {
  return SYSTEM_BY_ID.get(id);
}

export interface AnatomySearchResult {
  type: "system" | "structure";
  id: string;
  systemId: string;
  label: string;
  sublabel?: string;
}

/** Simple client-side substring search across systems and key structures. */
export function searchAnatomy(query: string, limit = 8): AnatomySearchResult[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];

  const results: AnatomySearchResult[] = [];

  for (const system of ANATOMY_SYSTEMS) {
    if (results.length >= limit) break;

    if (system.name.toLowerCase().includes(q) || system.shortName.toLowerCase().includes(q)) {
      results.push({ type: "system", id: system.id, systemId: system.id, label: system.name });
    }

    for (const structure of system.keyStructures) {
      if (results.length >= limit) break;
      if (structure.name.toLowerCase().includes(q)) {
        results.push({
          type: "structure",
          id: structure.id,
          systemId: system.id,
          label: structure.name,
          sublabel: system.name,
        });
      }
    }
  }

  return results.slice(0, limit);
}
