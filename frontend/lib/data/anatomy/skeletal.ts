import type { AnatomySystem } from "./types";

export const skeletal: AnatomySystem = {
  id: "skeletal",
  name: "Skeletal System",
  shortName: "Skeletal",
  description:
    "The skeletal system is the body's structural framework, made up of 206 bones in the adult body along with cartilage, ligaments, and connective tissue. It supports movement, protects vital organs, stores minerals, and produces blood cells within bone marrow.",
  keyStructures: [
    { id: "skull", name: "Skull", description: "Encases and protects the brain." },
    {
      id: "femur",
      name: "Femur",
      description: "The longest and strongest bone, extending from hip to knee.",
    },
    {
      id: "vertebrae",
      name: "Vertebrae",
      description: "33 stacked bones forming the spinal column.",
    },
    {
      id: "rib-cage",
      name: "Rib Cage",
      description: "12 paired bones protecting the heart and lungs.",
    },
    { id: "pelvis", name: "Pelvis", description: "Connects the spine to the lower limbs." },
  ],
  quickFacts: [
    ["Total bones", "206 (adult)"],
    ["Longest bone", "Femur"],
    ["Smallest bone", "Stapes (ear)"],
    ["Function", "Support & protection"],
  ],
  imagingAvailability: ["3D Anatomy", "X-Ray", "CT"],
  relatedSystemIds: ["muscular", "cardiovascular"],
};
