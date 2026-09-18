import type { AnatomySystem } from "./types";

export const urinary: AnatomySystem = {
  id: "urinary",
  name: "Urinary System",
  shortName: "Urinary",
  description:
    "The urinary system filters waste and excess fluid from the blood, producing urine for excretion. It consists of the kidneys, ureters, bladder, and urethra, and plays a key role in regulating fluid and electrolyte balance.",
  keyStructures: [
    { id: "kidneys", name: "Kidneys", description: "Filter blood and produce urine." },
    { id: "ureters", name: "Ureters", description: "Carry urine from kidneys to bladder." },
    { id: "bladder", name: "Bladder", description: "Stores urine until excretion." },
    { id: "urethra", name: "Urethra", description: "Channel through which urine exits the body." },
    {
      id: "renal-cortex",
      name: "Renal Cortex",
      description: "Outer kidney layer where filtration begins.",
    },
  ],
  quickFacts: [
    ["Kidneys", "2"],
    ["Blood filtered / day", "~180 liters"],
    ["Urine produced / day", "~1.5 liters"],
    ["Function", "Waste filtration"],
  ],
  imagingAvailability: ["3D Anatomy", "Ultrasound", "CT"],
  relatedSystemIds: ["digestive", "cardiovascular"],
};
