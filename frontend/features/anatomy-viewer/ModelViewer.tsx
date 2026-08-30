"use client";

import { Component, Suspense, type ReactNode } from "react";
import { Canvas } from "@react-three/fiber";
import { Center, OrbitControls, useGLTF } from "@react-three/drei";
import { AlertTriangleIcon } from "@/components/ui/icons";

interface ModelViewerProps {
  /** Web-relative path from manifest.json, e.g. "/models/cardiovascular/heart.glb" */
  path: string;
  /** Human-readable label for loading/error copy, e.g. "Heart" */
  label: string;
}

function Model({ path }: { path: string }) {
  const { scene } = useGLTF(path);
  return <primitive object={scene} />;
}

function LoadingOverlay({ label }: { label: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex h-full flex-col items-center justify-center gap-2"
    >
      <span className="size-2 animate-pulse rounded-full bg-accent" aria-hidden="true" />
      <p className="text-xs text-ink-subtle">Loading {label}…</p>
    </div>
  );
}

interface ErrorFallbackProps {
  label: string;
}

function ErrorFallback({ label }: ErrorFallbackProps) {
  return (
    <div
      role="alert"
      className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center"
    >
      <AlertTriangleIcon width={20} height={20} className="text-danger" />
      <p className="text-sm text-ink">Couldn&apos;t load the {label} model</p>
      <p className="max-w-xs text-xs text-ink-subtle">
        The GLB file may be missing or corrupted. Re-running the export pipeline usually fixes
        this.
      </p>
    </div>
  );
}

interface BoundaryProps {
  label: string;
  children: ReactNode;
}

interface BoundaryState {
  hasError: boolean;
}

/**
 * useGLTF suspends on load and throws on failure — React error boundaries
 * are the only way to catch that (no hook-based equivalent exists), so
 * this stays a small class component by necessity.
 */
class ModelErrorBoundary extends Component<BoundaryProps, BoundaryState> {
  override state: BoundaryState = { hasError: false };

  static getDerivedStateFromError(): BoundaryState {
    return { hasError: true };
  }

  override render() {
    if (this.state.hasError) {
      return <ErrorFallback label={this.props.label} />;
    }
    return this.props.children;
  }
}

/**
 * Renders one GLB model with orbit (rotate), zoom, and pan controls.
 * Client-only by necessity (WebGL) — never rendered outside a "use
 * client" tree, so it can't affect server-side rendering.
 *
 * Deliberately does not use drei's Stage/Environment helpers, which fetch
 * HDRI textures from an external CDN by default — lighting here is a
 * plain ambient + two directional lights instead, so the viewer has no
 * runtime dependency beyond the model file itself.
 */
export function ModelViewer({ path, label }: ModelViewerProps) {
  return (
    <div className="relative h-full w-full">
      <ModelErrorBoundary label={label}>
        <Suspense fallback={<LoadingOverlay label={label} />}>
          <Canvas
            camera={{ position: [0, 0, 3], fov: 45 }}
            dpr={[1, 2]}
            aria-label={`Interactive 3D model of ${label}`}
          >
            <ambientLight intensity={0.7} />
            <directionalLight position={[3, 5, 2]} intensity={1.2} />
            <directionalLight position={[-3, -2, -4]} intensity={0.4} />
            <Center>
              <Model path={path} />
            </Center>
            <OrbitControls enablePan enableZoom enableRotate makeDefault />
          </Canvas>
        </Suspense>
      </ModelErrorBoundary>
    </div>
  );
}
