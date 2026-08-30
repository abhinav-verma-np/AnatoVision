import { Suspense } from "react";
import { AppShell } from "@/components/layout/AppShell";

export default function HomePage() {
  // AppShell reads useSearchParams() (for ?structure=), which Next.js
  // requires to be wrapped in Suspense — otherwise the whole route would
  // silently opt out of static rendering.
  return (
    <Suspense fallback={<div className="h-screen bg-background" />}>
      <AppShell />
    </Suspense>
  );
}
