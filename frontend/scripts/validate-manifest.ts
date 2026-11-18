/**
 * Validates the manifest against the ACTUAL files on disk. Run against
 * whatever's really in frontend/public/models/ — no synthetic data.
 *
 * Usage:
 *   npm run validate-manifest
 *
 * Exits non-zero if any check fails, so it can be wired into CI later.
 */

import {
  closeSync,
  existsSync,
  globSync,
  openSync,
  readFileSync,
  readSync,
  statSync,
} from "node:fs";
import path from "node:path";
import { ANATOMY_SYSTEMS } from "../lib/data/anatomy";
import { resolveModel } from "../lib/modelResolver";
import type { Manifest } from "../lib/manifest";

const ROOT = path.resolve(__dirname, "..");
const MODELS_DIR = path.join(ROOT, "public/models");
const MANIFEST_PATH = path.join(MODELS_DIR, "manifest.json");

interface Issue {
  severity: "error" | "warning";
  message: string;
}

function loadManifest(): Record<string, unknown> {
  if (!existsSync(MANIFEST_PATH)) {
    throw new Error(`manifest.json not found at ${MANIFEST_PATH}`);
  }
  const raw = readFileSync(MANIFEST_PATH, "utf-8");
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch (err) {
    throw new Error(`manifest.json is not valid JSON: ${(err as Error).message}`);
  }
  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    throw new Error("manifest.json must be a JSON object");
  }
  // Intentionally untyped here (not cast to Manifest) — this validator's
  // job is to check whether the raw JSON actually matches that shape,
  // not to assume it does.
  return data as Record<string, unknown>;
}

function findAllGlbFiles(): string[] {
  // Recursive glob so this works regardless of which system-folder names
  // actually exist on disk — no hardcoded folder list.
  return globSync("**/*.glb", { cwd: MODELS_DIR }).map((p) => p.replace(/\\/g, "/"));
}

function validateManifestShape(manifest: Record<string, unknown>): Issue[] {
  const issues: Issue[] = [];
  for (const [key, entry] of Object.entries(manifest)) {
    if (typeof entry !== "object" || entry === null) {
      issues.push({
        severity: "error",
        message: `Malformed entry "${key}": not an object`,
      });
      continue;
    }
    const e = entry as Record<string, unknown>;
    if (typeof e.system !== "string" || e.system.length === 0) {
      issues.push({
        severity: "error",
        message: `Malformed entry "${key}": missing/invalid "system"`,
      });
    }
    if (typeof e.path !== "string" || !e.path.startsWith("/models/")) {
      issues.push({
        severity: "error",
        message: `Malformed entry "${key}": "path" must be a string starting with /models/`,
      });
    }
    if (typeof e.available !== "boolean") {
      issues.push({
        severity: "error",
        message: `Malformed entry "${key}": "available" must be a boolean`,
      });
    }
  }
  return issues;
}

function validatePathsExistOnDisk(manifest: Manifest): Issue[] {
  const issues: Issue[] = [];
  for (const [key, entry] of Object.entries(manifest)) {
    if (typeof entry?.path !== "string") continue;
    const relative = entry.path.replace(/^\/models\//, "");
    const absolute = path.join(MODELS_DIR, relative);
    const exists = existsSync(absolute) && statSync(absolute).isFile();
    if (!exists) {
      issues.push({
        severity: "error",
        message: `Manifest entry "${key}" points to a missing file: ${entry.path}`,
      });
    }
  }
  return issues;
}

function hasRenderableGeometry(glbPath: string): boolean {
  const fileSize = statSync(glbPath).size;
  const fd = openSync(glbPath, "r");
  try {
    const header = Buffer.alloc(20);
    if (readSync(fd, header, 0, header.length, 0) !== header.length) return false;
    if (
      header.toString("ascii", 0, 4) !== "glTF" ||
      header.readUInt32LE(4) !== 2 ||
      header.readUInt32LE(8) !== fileSize ||
      header.toString("ascii", 16, 20) !== "JSON"
    ) {
      return false;
    }

    const jsonLength = header.readUInt32LE(12);
    if (jsonLength > fileSize - header.length) return false;

    const jsonBuffer = Buffer.alloc(jsonLength);
    if (readSync(fd, jsonBuffer, 0, jsonLength, header.length) !== jsonLength)
      return false;
    const document: unknown = JSON.parse(
      jsonBuffer.toString("utf8").replace(/[\u0000 ]+$/g, ""),
    );
    if (typeof document !== "object" || document === null || !("meshes" in document)) {
      return false;
    }

    const { meshes, accessors } = document as {
      meshes?: Array<{ primitives?: Array<{ attributes?: { POSITION?: number } }> }>;
      accessors?: Array<{ count?: number }>;
    };
    return Boolean(
      meshes?.some((mesh) =>
        mesh.primitives?.some((primitive) => {
          const positionIndex = primitive.attributes?.POSITION;
          return (
            typeof positionIndex === "number" &&
            Number.isInteger(positionIndex) &&
            positionIndex >= 0 &&
            (accessors?.[positionIndex]?.count ?? 0) > 0
          );
        }),
      ),
    );
  } catch {
    return false;
  } finally {
    closeSync(fd);
  }
}

function validateAvailableModelsContainGeometry(manifest: Manifest): Issue[] {
  const issues: Issue[] = [];
  for (const [key, entry] of Object.entries(manifest)) {
    if (entry?.available !== true || typeof entry.path !== "string") continue;
    const absolute = path.join(MODELS_DIR, entry.path.replace(/^\/models\//, ""));
    if (
      existsSync(absolute) &&
      statSync(absolute).isFile() &&
      !hasRenderableGeometry(absolute)
    ) {
      issues.push({
        severity: "error",
        message: `Manifest entry "${key}" claims available:true, but its GLB contains no renderable mesh geometry: ${entry.path}`,
      });
    }
  }
  return issues;
}

function validateNoDuplicatePaths(manifest: Manifest): Issue[] {
  const issues: Issue[] = [];
  const seen = new Map<string, string>();
  for (const [key, entry] of Object.entries(manifest)) {
    if (typeof entry?.path !== "string") continue;
    const existing = seen.get(entry.path);
    if (existing) {
      issues.push({
        severity: "error",
        message: `Duplicate path "${entry.path}" used by both "${existing}" and "${key}"`,
      });
    } else {
      seen.set(entry.path, key);
    }
  }
  return issues;
}

function validateGlbsRepresentedInManifest(manifest: Manifest): Issue[] {
  const issues: Issue[] = [];
  const manifestPaths = new Set(
    Object.values(manifest)
      .map((e) =>
        typeof e?.path === "string" ? e.path.replace(/^\/models\//, "") : null,
      )
      .filter((p): p is string => p !== null),
  );
  for (const glb of findAllGlbFiles()) {
    if (!manifestPaths.has(glb)) {
      issues.push({
        severity: "warning",
        message: `GLB on disk has no manifest entry: ${glb}`,
      });
    }
  }
  return issues;
}

function validateNoFalseAvailability(manifest: Manifest): Issue[] {
  // For every KeyStructure the resolver claims is available, confirm the
  // underlying GLB genuinely exists on disk — checked through the actual
  // resolver path the app uses, not raw manifest iteration.
  const issues: Issue[] = [];
  for (const system of ANATOMY_SYSTEMS) {
    for (const structure of system.keyStructures) {
      const resolved = resolveModel(manifest, structure);
      if (resolved?.available) {
        const absolute = path.join(MODELS_DIR, resolved.path.replace(/^\/models\//, ""));
        if (!existsSync(absolute)) {
          issues.push({
            severity: "error",
            message: `Structure "${structure.name}" (${structure.id}) resolves to "${resolved.id}" claiming available:true, but the file is missing: ${resolved.path}`,
          });
        }
      }
    }
  }
  return issues;
}

function validateAllAvailableModelsRepresented(manifest: Manifest): Issue[] {
  const issues: Issue[] = [];
  const representedKeys = new Set<string>();
  for (const system of ANATOMY_SYSTEMS) {
    for (const structure of system.keyStructures) {
      const resolved = resolveModel(manifest, structure);
      if (resolved) representedKeys.add(resolved.id);
    }
  }
  for (const [key, entry] of Object.entries(manifest)) {
    if (entry?.available === true && !representedKeys.has(key)) {
      issues.push({
        severity: "warning",
        message: `Available manifest model "${key}" is not represented by any catalog entry — run \`npm run generate-catalog\`.`,
      });
    }
  }
  return issues;
}

function main(): void {
  console.log(`Validating manifest at: ${MANIFEST_PATH}`);
  console.log(`Scanning GLBs under   : ${MODELS_DIR}\n`);

  const glbFiles = findAllGlbFiles();
  console.log(`GLB files found on disk: ${glbFiles.length}`);

  const rawManifest = loadManifest();
  console.log(`Manifest entries       : ${Object.keys(rawManifest).length}\n`);

  const shapeIssues = validateManifestShape(rawManifest);

  // The remaining checks assume the manifest roughly matches its expected
  // shape (they defensively skip anything that doesn't); shape problems
  // are already reported above regardless.
  const manifest = rawManifest as Manifest;

  const allIssues: Issue[] = [
    ...shapeIssues,
    ...validatePathsExistOnDisk(manifest),
    ...validateAvailableModelsContainGeometry(manifest),
    ...validateNoDuplicatePaths(manifest),
    ...validateGlbsRepresentedInManifest(manifest),
    ...validateNoFalseAvailability(manifest),
    ...validateAllAvailableModelsRepresented(manifest),
  ];

  const errors = allIssues.filter((i) => i.severity === "error");
  const warnings = allIssues.filter((i) => i.severity === "warning");

  for (const issue of allIssues) {
    console.log(`[${issue.severity.toUpperCase()}] ${issue.message}`);
  }

  console.log(`\nErrors: ${errors.length}  Warnings: ${warnings.length}`);

  if (errors.length > 0) {
    console.log("\nVALIDATION FAILED");
    process.exitCode = 1;
  } else {
    console.log("\nVALIDATION PASSED");
  }
}

main();
