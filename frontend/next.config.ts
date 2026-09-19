import path from "node:path";
import type { NextConfig } from "next";

/**
 * AnatoVision — Next.js configuration.
 *
 * Kept intentionally minimal for Phase 1 (foundation only). Future phases
 * that add DICOM/imaging asset loading, remote dataset image domains, or
 * WASM-based tooling (itk.js / vtk.js) should extend this file rather than
 * replace it.
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: path.join(__dirname, ".."),
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "img.abhinavverma.com.np",
        pathname: "/anstovision-logo.png",
      },
    ],
  },

  // Standalone output keeps the Docker runtime image small (see
  // docker/../frontend/Dockerfile) by tracing only the files each route
  // actually needs instead of shipping the full node_modules tree.

  // Fails the production build on type errors instead of silently shipping
  // broken code — this is an educational platform, correctness first.
  // (Next.js 16 removed the built-in `eslint` build-config key; lint is run
  // as its own CI/Makefile step instead — see `npm run lint`.)
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
