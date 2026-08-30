import type { AnatomySystem } from "./types";

export const nervous: AnatomySystem = {
  id: "nervous",
  name: "Nervous System",
  shortName: "Nervous",
  description:
    "The nervous system is the body's communication network, made up of the brain, spinal cord, and peripheral nerves. It processes sensory input, coordinates voluntary and involuntary actions, and enables thought, memory, and reflexes.",
  keyStructures: [
    { id: "brain", name: "Brain", description: "Central processing organ for thought and control." },
    {
      id: "spinal-cord",
      name: "Spinal Cord",
      description: "Relays signals between the brain and body.",
    },
    { id: "cerebellum", name: "Cerebellum", description: "Coordinates balance and fine movement." },
    {
      id: "peripheral-nerves",
      name: "Peripheral Nerves",
      description: "Carry signals to and from limbs and organs.",
    },
    {
      id: "cranial-nerves",
      name: "Cranial Nerves",
      description: "12 pairs controlling head and neck function.",
    },
  ],
  quickFacts: [
    ["Brain weight", "~1.4 kg"],
    ["Neurons", "~86 billion"],
    ["Divisions", "CNS & PNS"],
    ["Function", "Signal processing & control"],
  ],
  imagingAvailability: ["3D Anatomy", "MRI", "CT"],
  relatedSystemIds: ["cardiovascular", "muscular"],
};
