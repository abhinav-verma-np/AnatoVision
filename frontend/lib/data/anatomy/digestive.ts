import type { AnatomySystem } from "./types";

export const digestive: AnatomySystem = {
  id: "digestive",
  name: "Digestive System",
  shortName: "Digestive",
  description:
    "The digestive system breaks down food into nutrients the body can absorb and use for energy, growth, and repair. It spans from the mouth to the anus, including the stomach, intestines, liver, and pancreas.",
  keyStructures: [
    { id: "stomach", name: "Stomach", description: "Breaks down food with acid and enzymes." },
    {
      id: "small-intestine",
      name: "Small Intestine",
      description: "Primary site of nutrient absorption.",
    },
    {
      id: "large-intestine",
      name: "Large Intestine",
      description: "Absorbs water and forms waste.",
    },
    { id: "liver", name: "Liver", description: "Processes nutrients and filters toxins." },
    { id: "pancreas", name: "Pancreas", description: "Produces digestive enzymes and insulin." },
  ],
  quickFacts: [
    ["Total length", "~9 meters"],
    ["Digestion time", "24–72 hours"],
    ["Key organ", "Liver"],
    ["Function", "Nutrient absorption"],
  ],
  imagingAvailability: ["3D Anatomy", "CT", "Ultrasound"],
  relatedSystemIds: ["urinary", "cardiovascular"],
};
