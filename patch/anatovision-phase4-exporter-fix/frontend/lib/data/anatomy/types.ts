export interface KeyStructure {
  id: string;
  name: string;
  description: string;
  /** Ordered candidate real Z-Anatomy manifest keys to try when `id` itself
   * isn't a manifest key (Z-Anatomy's export names follow its own
   * Terminologia Anatomica-derived convention, e.g.
   * "bones-of-free-lower-limb", not our simple content slugs). Optional —
   * omit until confirmed against the real manifest.json; see
   * lib/modelResolver.ts. */
  manifestAliases?: string[];
}

export type ImagingModality = "3D Anatomy" | "X-Ray" | "CT" | "MRI" | "Ultrasound" | "PET/SPECT";

export interface AnatomySystem {
  id: string;
  name: string;
  shortName: string;
  description: string;
  keyStructures: KeyStructure[];
  quickFacts: Array<[string, string]>;
  imagingAvailability: ImagingModality[];
  relatedSystemIds: string[];
}
