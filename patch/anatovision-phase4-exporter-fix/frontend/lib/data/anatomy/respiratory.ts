import type { AnatomySystem } from "./types";

export const respiratory: AnatomySystem = {
  id: "respiratory",
  name: "Respiratory System",
  shortName: "Respiratory",
  description:
    "The respiratory system enables gas exchange, bringing oxygen into the body and removing carbon dioxide. It includes the nose, trachea, bronchi, and lungs, working closely with the cardiovascular system to oxygenate blood.",
  keyStructures: [
    { id: "lungs", name: "Lungs", description: "Paired organs where gas exchange occurs." },
    { id: "trachea", name: "Trachea", description: "The windpipe connecting throat to lungs." },
    { id: "bronchi", name: "Bronchi", description: "Airway branches leading into each lung." },
    { id: "diaphragm-resp", name: "Diaphragm", description: "Drives inhalation and exhalation." },
    { id: "alveoli", name: "Alveoli", description: "Tiny air sacs where oxygen enters the blood." },
  ],
  quickFacts: [
    ["Breaths per minute", "12–20 (resting)"],
    ["Lung lobes", "3 right, 2 left"],
    ["Gas exchange site", "Alveoli"],
    ["Function", "Oxygen / CO2 exchange"],
  ],
  imagingAvailability: ["3D Anatomy", "X-Ray", "CT"],
  relatedSystemIds: ["cardiovascular", "muscular"],
};
