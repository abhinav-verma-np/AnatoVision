import type { AnatomySystem } from "./types";

export const muscular: AnatomySystem = {
  id: "muscular",
  name: "Muscular System",
  shortName: "Muscular",
  description:
    "The muscular system consists of over 600 skeletal, smooth, and cardiac muscles that enable movement, maintain posture, and generate body heat. Skeletal muscles attach to bone via tendons and contract voluntarily to produce motion.",
  keyStructures: [
    {
      id: "biceps-brachii",
      name: "Biceps Brachii",
      description: "Flexes the elbow and rotates the forearm.",
    },
    { id: "quadriceps", name: "Quadriceps", description: "Extends the knee for walking and standing." },
    { id: "deltoid", name: "Deltoid", description: "Rounds the shoulder and lifts the arm." },
    {
      id: "gastrocnemius",
      name: "Gastrocnemius",
      description: "Calf muscle powering ankle push-off.",
    },
    { id: "diaphragm", name: "Diaphragm", description: "The primary muscle of breathing." },
  ],
  quickFacts: [
    ["Total muscles", "~600+"],
    ["Largest muscle", "Gluteus maximus"],
    ["Muscle types", "Skeletal, smooth, cardiac"],
    ["Function", "Movement & posture"],
  ],
  imagingAvailability: ["3D Anatomy", "Ultrasound", "MRI"],
  relatedSystemIds: ["skeletal", "nervous"],
};
