"""
AnatoVision Z-Anatomy asset pipeline — main entrypoint.

    python scripts/process_models.py

Scans assets/raw/Z-Anatomy/ for supported 3D model files, converts each
to .glb, classifies it into a body system via config/model_mapping.json,
places it under frontend/public/models/<system>/, and regenerates
frontend/public/models/manifest.json. One model failing never stops the
run — everything is logged and summarized at the end.

This script never downloads anything. The developer is responsible for
manually downloading/extracting the Z-Anatomy repository into
assets/raw/Z-Anatomy/ first.
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from compression import CompressionMethod, compress_glb
from generate_manifest import generate_manifest, write_manifest
from model_convert import convert_to_glb
from pipeline_common import (
    DEFAULT_LOG_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_MAPPING_PATH,
    DEFAULT_MODELS_DIR,
    DEFAULT_RAW_DIR,
    SUPPORTED_EXTENSIONS,
    ProcessResult,
    classify_model,
    ensure_output_dirs,
    format_duration,
    load_model_mapping,
    setup_logger,
    slugify,
)


def scan_source_files(raw_dir: Path) -> list[Path]:
    """Recursively find every supported model file under raw_dir, skipping
    anything with an unsupported extension safely (no error, just excluded)."""
    if not raw_dir.exists():
        return []
    return sorted(
        p for p in raw_dir.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def process_one(
    source: Path,
    models_dir: Path,
    mapping: dict[str, str],
    blender_exe: str,
    compression: CompressionMethod,
    force: bool,
    dry_run: bool,
) -> ProcessResult:
    start = time.perf_counter()
    original_stem = source.stem
    slug = slugify(original_stem)
    system = classify_model(original_stem, mapping)
    output_path = models_dir / system / f"{slug}.glb"

    if output_path.exists() and not force:
        return ProcessResult(
            name=slug,
            source=source,
            system=system,
            output=output_path,
            status="skipped",
            reason="already processed (use --force to reprocess)",
            elapsed_seconds=time.perf_counter() - start,
        )

    if dry_run:
        return ProcessResult(
            name=slug,
            source=source,
            system=system,
            output=output_path,
            status="skipped",
            reason="dry run",
            elapsed_seconds=time.perf_counter() - start,
        )

    success, message = convert_to_glb(source, output_path, blender_exe=blender_exe)

    if not success:
        output_path.unlink(missing_ok=True)
        return ProcessResult(
            name=slug,
            source=source,
            system=system,
            output=None,
            status="failed",
            reason=message,
            elapsed_seconds=time.perf_counter() - start,
        )

    compress_glb(output_path, method=compression)

    return ProcessResult(
        name=slug,
        source=source,
        system=system,
        output=output_path,
        status="processed",
        reason=message,
        elapsed_seconds=time.perf_counter() - start,
    )


def print_summary(results: list[ProcessResult], total_elapsed: float) -> None:
    processed = [r for r in results if r.status == "processed"]
    skipped = [r for r in results if r.status == "skipped"]
    failed = [r for r in results if r.status == "failed"]

    print()
    print("=" * 60)
    print("AnatoVision asset pipeline — summary")
    print("=" * 60)
    print(f"  Processed : {len(processed)}")
    print(f"  Skipped   : {len(skipped)}")
    print(f"  Failed    : {len(failed)}")
    print(f"  Elapsed   : {format_duration(total_elapsed)}")

    if failed:
        print()
        print("  Failed models:")
        for r in failed:
            print(f"    - {r.source.name}: {r.reason}")

    print("=" * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process the local Z-Anatomy dataset into optimized GLB assets."
    )
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_MODELS_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING_PATH)
    parser.add_argument("--log-file", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument(
        "--blender-exe",
        type=str,
        default=os.environ.get("BLENDER_EXE", "blender"),
        help="Path to the Blender executable (default: 'blender' on PATH, or $BLENDER_EXE)",
    )
    parser.add_argument(
        "--compress",
        choices=("none", "draco", "meshopt"),
        default="none",
        help="Post-export compression via gltf-transform, if installed (default: none)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Reprocess models even if their .glb already exists"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Scan and classify only — no conversion or writes"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger = setup_logger(args.log_file)
    run_start = time.perf_counter()

    logger.info("AnatoVision asset pipeline starting")
    logger.info("  raw dir     : %s", args.raw_dir)
    logger.info("  output dir  : %s", args.output_dir)
    logger.info("  mapping     : %s", args.mapping)
    logger.info("  compression : %s", args.compress)
    logger.info("  dry run     : %s", args.dry_run)

    if not args.raw_dir.exists():
        logger.error(
            "Raw dataset directory not found: %s\n"
            "  Download the Z-Anatomy repository and extract it there first "
            "(this pipeline never downloads assets automatically).",
            args.raw_dir,
        )
        return

    ensure_output_dirs(args.output_dir)
    mapping = load_model_mapping(args.mapping)
    logger.info("Loaded %d classification keywords from %s", len(mapping), args.mapping)

    sources = scan_source_files(args.raw_dir)
    logger.info("Found %d supported model file(s) in %s", len(sources), args.raw_dir)

    if not sources:
        logger.warning("Nothing to process — no supported files found.")
        return

    results: list[ProcessResult] = []
    for index, source in enumerate(sources, start=1):
        logger.info("[%d/%d] %s", index, len(sources), source.relative_to(args.raw_dir))
        try:
            result = process_one(
                source=source,
                models_dir=args.output_dir,
                mapping=mapping,
                blender_exe=args.blender_exe,
                compression=args.compress,  # type: ignore[arg-type]
                force=args.force,
                dry_run=args.dry_run,
            )
        except Exception as exc:  # noqa: BLE001 - one model's crash must not kill the run
            logger.exception("Unexpected error processing %s", source)
            result = ProcessResult(
                name=slugify(source.stem),
                source=source,
                system="unclassified",
                output=None,
                status="failed",
                reason=f"unexpected error: {exc}",
            )

        results.append(result)

        if result.status == "processed":
            logger.info(
                "  -> processed: %s [%s] (%s)",
                result.output,
                result.system,
                format_duration(result.elapsed_seconds),
            )
        elif result.status == "skipped":
            logger.info("  -> skipped: %s", result.reason)
        else:
            logger.error("  -> failed: %s", result.reason)

    if not args.dry_run:
        manifest = generate_manifest(args.output_dir)
        write_manifest(manifest, args.manifest)
        logger.info("Manifest written: %s (%d models)", args.manifest, len(manifest))

    total_elapsed = time.perf_counter() - run_start
    print_summary(results, total_elapsed)
    logger.info(
        "Pipeline finished in %s — processed=%d skipped=%d failed=%d",
        format_duration(total_elapsed),
        sum(1 for r in results if r.status == "processed"),
        sum(1 for r in results if r.status == "skipped"),
        sum(1 for r in results if r.status == "failed"),
    )


if __name__ == "__main__":
    main()
