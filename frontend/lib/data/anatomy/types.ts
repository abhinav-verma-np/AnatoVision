export interface KeyStructure {
  id: string;
  name: string;
  description: string;
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
