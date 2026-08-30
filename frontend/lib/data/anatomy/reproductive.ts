import type { AnatomySystem } from "./types";

export const reproductive: AnatomySystem = {
  id: "reproductive",
  name: "Reproductive System",
  shortName: "Reproductive",
  description:
    "The reproductive system enables the production of offspring and the development of secondary sexual characteristics. Male and female systems differ structurally but both are regulated by hormonal signals from the endocrine system.",
  keyStructures: [
    { id: "ovaries", name: "Ovaries", description: "Produce eggs and female sex hormones." },
    { id: "uterus", name: "Uterus", description: "Site of fetal development during pregnancy." },
    { id: "testes", name: "Testes", description: "Produce sperm and male sex hormones." },
    { id: "prostate", name: "Prostate", description: "Contributes fluid to semen." },
    {
      id: "reproductive-ducts",
      name: "Reproductive Ducts",
      description: "Pathways connecting reproductive organs.",
    },
  ],
  quickFacts: [
    ["Regulated by", "Endocrine system"],
    ["Female key organ", "Uterus"],
    ["Male key organ", "Testes"],
    ["Function", "Reproduction"],
  ],
  imagingAvailability: ["3D Anatomy", "Ultrasound", "MRI"],
  relatedSystemIds: ["urinary", "nervous"],
};
