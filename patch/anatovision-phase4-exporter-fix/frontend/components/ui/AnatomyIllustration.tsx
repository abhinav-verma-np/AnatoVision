interface AnatomyIllustrationProps {
  systemId: string;
  className?: string;
}

/**
 * Abstract, schematic line-art per body system — deliberately not
 * anatomically precise. Stands in for the real 3D/imaging viewers built
 * in a later phase.
 */
export function AnatomyIllustration({ systemId, className }: AnatomyIllustrationProps) {
  const common = {
    width: 96,
    height: 96,
    viewBox: "0 0 64 64",
    fill: "none" as const,
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className,
    "aria-hidden": true,
  };

  switch (systemId) {
    case "skeletal":
      return (
        <svg {...common}>
          <path d="M32 8c-9 0-16 6.5-16 15 0 6 3 9.5 5 12v6a3 3 0 0 0 3 3h16a3 3 0 0 0 3-3v-6c2-2.5 5-6 5-12 0-8.5-7-15-16-15Z" />
          <circle cx="26" cy="24" r="2.2" />
          <circle cx="38" cy="24" r="2.2" />
          <path d="M29 32h6" />
          <path d="M28 44v6h8v-6" />
        </svg>
      );
    case "muscular":
      return (
        <svg {...common}>
          <path d="M14 40c0-10 4-18 10-22 3-2 5 1 4 4-2 5-1 9 3 9 5 0 6-6 11-6 5 0 8 5 8 11 0 9-7 14-16 14-11 0-20-3-20-10Z" />
          <path d="M28 22c2 2 2 6 0 9" />
        </svg>
      );
    case "nervous":
      return (
        <svg {...common}>
          <path d="M32 10c7 0 12 5 12 11 0 3-1 5-3 7 1 2 1 4 0 6 1 2 0 5-2 6-1 3-4 4-7 4s-6-1-7-4c-2-1-3-4-2-6-1-2-1-4 0-6-2-2-3-4-3-7 0-6 5-11 12-11Z" />
          <path d="M32 10v26" />
          <path d="M25 18c2 1 2 4 0 6M39 18c-2 1-2 4 0 6" />
          <path d="M26 30c2 1 4 1 6 0M32 30c2 1 4 1 6 0" />
        </svg>
      );
    case "cardiovascular":
      return (
        <svg {...common}>
          <path d="M32 46S14 34 14 21c0-6 5-10 10-10 4 0 7 2 8 6 1-4 4-6 8-6 5 0 10 4 10 10 0 13-18 25-18 25Z" />
          <path d="M20 27h6l3-6 4 10 3-6h8" />
        </svg>
      );
    case "respiratory":
      return (
        <svg {...common}>
          <path d="M32 10v14" />
          <path d="M32 24c-4-6-14-4-16 3-2 8 2 18 10 18 4 0 6-3 6-7" />
          <path d="M32 24c4-6 14-4 16 3 2 8-2 18-10 18-4 0-6-3-6-7" />
        </svg>
      );
    case "digestive":
      return (
        <svg {...common}>
          <path d="M26 10c-3 4-4 8-2 12 3 5-2 8-2 13 0 7 6 11 12 11s11-5 11-12c0-5-3-8-6-10-4-3-3-7-1-10" />
        </svg>
      );
    case "urinary":
      return (
        <svg {...common}>
          <path d="M24 14c-6 0-8 6-6 11 1 3 0 5-1 7-2 4 0 9 5 9 3 0 5-2 6-5" />
          <path d="M40 14c6 0 8 6 6 11-1 3 0 5 1 7 2 4 0 9-5 9-3 0-5-2-6-5" />
          <path d="M28 40v6M36 40v6" />
        </svg>
      );
    case "reproductive":
      return (
        <svg {...common}>
          <circle cx="32" cy="24" r="10" />
          <path d="M32 34v14M25 44h14" />
        </svg>
      );
    default:
      return (
        <svg {...common}>
          <rect x="10" y="10" width="44" height="44" rx="6" />
          <path d="M10 38l11-11a5 5 0 0 1 7 0L38 38" />
          <circle cx="24" cy="22" r="3.5" />
        </svg>
      );
  }
}
