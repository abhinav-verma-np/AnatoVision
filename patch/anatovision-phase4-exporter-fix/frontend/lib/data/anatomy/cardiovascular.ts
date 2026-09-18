import type { AnatomySystem } from "./types";

export const cardiovascular: AnatomySystem = {
  id: "cardiovascular",
  name: "Cardiovascular System",
  shortName: "Cardiovascular",
  description:
    "The cardiovascular system circulates blood throughout the body via the heart, arteries, veins, and capillaries. It delivers oxygen and nutrients to tissues, removes waste products, and helps regulate body temperature and pH.",
  keyStructures: [
    { id: "heart", name: "Heart", description: "Four-chambered pump driving circulation." },
    { id: "aorta", name: "Aorta", description: "The body's largest artery." },
    {
      id: "coronary-arteries",
      name: "Coronary Arteries",
      description: "Supply oxygenated blood to the heart muscle.",
    },
    { id: "vena-cava", name: "Vena Cava", description: "Returns deoxygenated blood to the heart." },
    {
      id: "capillary-network",
      name: "Capillary Network",
      description: "Site of oxygen and nutrient exchange.",
    },
  ],
  quickFacts: [
    ["Resting heart rate", "60–100 bpm"],
    ["Blood volume", "~5 liters"],
    ["Heart chambers", "4"],
    ["Function", "Circulation"],
  ],
  imagingAvailability: ["3D Anatomy", "Ultrasound", "CT", "MRI"],
  relatedSystemIds: ["respiratory", "nervous"],
};
