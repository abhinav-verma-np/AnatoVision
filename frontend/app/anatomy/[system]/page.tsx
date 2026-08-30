import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ANATOMY_SYSTEMS, getSystemById } from "@/lib/data/anatomy";
import { AppShell } from "@/components/layout/AppShell";

interface AnatomySystemPageProps {
  params: Promise<{ system: string }>;
}

export function generateStaticParams() {
  return ANATOMY_SYSTEMS.map((system) => ({ system: system.id }));
}

export async function generateMetadata({
  params,
}: AnatomySystemPageProps): Promise<Metadata> {
  const { system: systemId } = await params;
  const system = getSystemById(systemId);
  if (!system) return {};

  return {
    title: `${system.name} — AnatoVision`,
    description: system.description,
  };
}

/** Direct loads of /anatomy/skeletal, /anatomy/cardiovascular, etc. all
 * resolve here. AppShell reads the `system` route param itself via
 * useParams(), so no props are threaded through. */
export default async function AnatomySystemPage({ params }: AnatomySystemPageProps) {
  const { system: systemId } = await params;
  const system = getSystemById(systemId);
  if (!system) notFound();

  return <AppShell />;
}
