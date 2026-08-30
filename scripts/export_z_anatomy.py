"""
AnatoVision Z-Anatomy Native Exporter — main entrypoint.

    python scripts/export_z_anatomy.py

Detects Blender and the installed Z-Anatomy Application Template, then:

  1. Runs ONE lightweight Blender pass (dry-run) to list every collection
     in the atlas — no export operator calls happen here, so it stays
     fast even across hundreds of collections.
  2. Exports each collection in its OWN Blender subprocess, with its own
     timeout (--collection-timeout, default 300s). One slow or stuck
     collection can only ever fail that one subprocess — it can no longer
     time out the entire run.
  3. Checkpoints after every collection (logs/export_checkpoint.json) and
     regenerates manifest.json incrementally, so an interrupted run can
     be resumed by simply re-running the same command — already-completed
     collections are skipped automatically.

Permanent project rule: the installed Z-Anatomy template is treated as
read-only. This script never modifies it and never downloads it — the
developer installs Z-Anatomy.zip into Blender themselves, once.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from compression import compress_glb
from generate_manifest import generate_manifest, write_manifest
from pipeline_common import (
    DEFAULT_CHECKPOINT_PATH,
    DEFAULT_COLLECTION_EXPORT_SCRIPT,
    DEFAULT_LOG_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_MAPPING_PATH,
    DEFAULT_MODELS_DIR,
    DEFAULT_TEMPLATE_NAME,
    CollectionExportResult,
    ensure_output_dirs,
    find_blender_executable,
    find_z_anatomy_template,
    format_duration,
    load_checkpoint,
    save_checkpoint,
    setup_logger,
    suggest_template_install_path,
)

# One-time full-atlas scan (dry-run, no exports) — fast, so a generous
# fixed timeout is fine without needing its own CLI flag.
LISTING_TIMEOUT_SECONDS = 600
DEFAULT_COLLECTION_TIMEOUT_SECONDS = 300


def _make_temp_report_path() -> Path:
    fd, path_str = tempfile.mkstemp(suffix=".json", prefix="anatovision_export_report_")
    os.close(fd)
    return Path(path_str)


def run_blender_export(
    blender_exe: str,
    template_name: str,
    output_dir: Path,
    mapping_path: Path,
    report_path: Path,
    log_path: Path,
    force: bool,
    dry_run: bool,
    only_collection: str,
    timeout: int,
) -> tuple[bool, str]:
    """Launch one Blender background subprocess. When only_collection is
    empty, Blender walks and reports on the whole atlas (used for the
    listing pass); when set, it exports exactly that one collection."""
    command = [
        blender_exe,
        "--background",
        "--factory-startup",
        "--app-template",
        template_name,
        "--python",
        str(DEFAULT_COLLECTION_EXPORT_SCRIPT),
        "--",
        str(output_dir),
        str(mapping_path),
        str(report_path),
        str(log_path),
        "1" if force else "0",
        "1" if dry_run else "0",
        only_collection,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return False, f"Blender executable not found: {blender_exe}"
    except subprocess.TimeoutExpired:
        return False, f"Blender timed out after {timeout}s"

    if result.returncode != 0 and not report_path.exists():
        stderr_tail = (result.stderr or "").strip()[-800:]
        return False, f"Blender exited {result.returncode} before writing a report: {stderr_tail}"

    return True, "ok"


def load_report(report_path: Path) -> list[CollectionExportResult]:
    with report_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [CollectionExportResult.from_dict(entry) for entry in raw]


def print_summary(results: list[CollectionExportResult], total_elapsed: float) -> None:
    processed = [r for r in results if r.status == "processed"]
    skipped = [r for r in results if r.status == "skipped"]
    failed = [r for r in results if r.status == "failed"]

    print()
    print("=" * 60)
    print("AnatoVision Z-Anatomy Native Exporter — summary")
    print("=" * 60)
    print(f"  Processed : {len(processed)}")
    print(f"  Skipped   : {len(skipped)}")
    print(f"  Failed    : {len(failed)}")
    print(f"  Elapsed   : {format_duration(total_elapsed)}")

    if failed:
        print()
        print("  Failed collections:")
        for r in failed:
            print(f"    - {r.collection_path}: {r.reason}")

    print("=" * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the installed Z-Anatomy Blender Application Template into GLB assets."
    )
    parser.add_argument(
        "--blender-exe",
        type=str,
        default=os.environ.get("BLENDER_EXE", "blender"),
        help="Path to the Blender executable (default: 'blender' on PATH, or $BLENDER_EXE)",
    )
    parser.add_argument("--template-name", type=str, default=DEFAULT_TEMPLATE_NAME)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_MODELS_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING_PATH)
    parser.add_argument("--log-file", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--checkpoint-file", type=Path, default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument(
        "--collection-timeout",
        type=int,
        default=DEFAULT_COLLECTION_TIMEOUT_SECONDS,
        help=f"Per-collection Blender subprocess timeout in seconds "
        f"(default: {DEFAULT_COLLECTION_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--compress",
        choices=("none", "draco", "meshopt"),
        default="none",
        help="Post-export compression via gltf-transform, if installed (default: none)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-export collections even if already exported or checkpointed "
        "(disables resume; default behavior is to resume automatically)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List and classify only — no export or writes"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger = setup_logger(args.log_file)
    run_start = time.perf_counter()

    logger.info("AnatoVision Z-Anatomy Native Exporter starting")
    logger.info("  template          : %s", args.template_name)
    logger.info("  output dir        : %s", args.output_dir)
    logger.info("  compression       : %s", args.compress)
    logger.info("  collection timeout: %ss", args.collection_timeout)
    logger.info("  dry run           : %s", args.dry_run)
    logger.info("  resume (default)  : %s", not args.force)

    blender_exe = find_blender_executable(args.blender_exe)
    if blender_exe is None:
        logger.error(
            "Blender not found ('%s'). Install Blender from "
            "https://www.blender.org/download/ and ensure it's on PATH, "
            "or pass --blender-exe / set BLENDER_EXE.",
            args.blender_exe,
        )
        return
    logger.info("Detected Blender: %s", blender_exe)

    template_dir = find_z_anatomy_template(args.template_name)
    if template_dir is None:
        suggested = suggest_template_install_path(args.template_name)
        logger.error(
            "Z-Anatomy Application Template not found.\n"
            "  This pipeline never installs it automatically — install it yourself:\n"
            "    1. Download the official Z-Anatomy.zip release.\n"
            "    2. In Blender: File > Install Application Template... and select "
            "Z-Anatomy.zip\n"
            "       (or extract it manually into: %s)\n"
            "    3. Restart Blender once so it registers the template, then re-run "
            "this script.",
            suggested,
        )
        return
    logger.info("Detected Z-Anatomy template: %s", template_dir)

    ensure_output_dirs(args.output_dir)
    checkpoint = load_checkpoint(args.checkpoint_file)
    logger.info(
        "Loaded checkpoint: %s (%d previously-recorded collection(s))",
        args.checkpoint_file,
        len(checkpoint),
    )

    # --- Phase 1: one fast, non-exporting pass to list every collection ---
    logger.info("Scanning Z-Anatomy atlas for collections (listing pass)…")
    listing_report_path = _make_temp_report_path()
    try:
        launched, message = run_blender_export(
            blender_exe=blender_exe,
            template_name=args.template_name,
            output_dir=args.output_dir,
            mapping_path=args.mapping,
            report_path=listing_report_path,
            log_path=args.log_file,
            force=False,  # listing never writes files regardless
            dry_run=True,
            only_collection="",
            timeout=LISTING_TIMEOUT_SECONDS,
        )
        if not launched:
            logger.error("Failed to list collections: %s", message)
            return
        if not listing_report_path.exists():
            logger.error(
                "Blender ran but produced no listing — check %s for details.", args.log_file
            )
            return
        all_items = load_report(listing_report_path)
    finally:
        listing_report_path.unlink(missing_ok=True)

    total = len(all_items)
    logger.info("Found %d collection(s) in the atlas", total)
    if total == 0:
        logger.warning("Nothing to export — no collections with mesh objects were found.")
        return

    # --- Phase 2: export (or skip) each collection, one subprocess each ---
    results: list[CollectionExportResult] = []

    for index, item in enumerate(all_items, start=1):
        path = item.collection_path
        print(f"[{index}/{total}] Exporting {path}")

        already_done = not args.force and (
            (item.output is not None and item.output.exists())
            or checkpoint.get(path, {}).get("status") == "processed"
        )

        if already_done:
            logger.info("[%d/%d]   skipped (resumed): %s", index, total, path)
            results.append(
                CollectionExportResult(
                    name=item.name,
                    collection_path=path,
                    system=item.system,
                    output=item.output,
                    status="skipped",
                    reason="already exported (resumed from checkpoint)",
                )
            )
            continue

        if args.dry_run:
            results.append(item)
            continue

        collection_report_path = _make_temp_report_path()
        try:
            launched, message = run_blender_export(
                blender_exe=blender_exe,
                template_name=args.template_name,
                output_dir=args.output_dir,
                mapping_path=args.mapping,
                report_path=collection_report_path,
                log_path=args.log_file,
                force=args.force,
                dry_run=False,
                only_collection=path,
                timeout=args.collection_timeout,
            )

            if not launched:
                result = CollectionExportResult(
                    name=item.name,
                    collection_path=path,
                    system=item.system,
                    output=None,
                    status="failed",
                    reason=message,
                )
            else:
                sub_results = (
                    load_report(collection_report_path) if collection_report_path.exists() else []
                )
                result = (
                    sub_results[0]
                    if sub_results
                    else CollectionExportResult(
                        name=item.name,
                        collection_path=path,
                        system=item.system,
                        output=None,
                        status="failed",
                        reason="Blender ran but reported no result for this collection",
                    )
                )
        finally:
            collection_report_path.unlink(missing_ok=True)

        results.append(result)

        # Checkpoint immediately — this is what makes the next run resumable
        # even if this run gets interrupted right after this line.
        checkpoint[path] = {
            "status": result.status,
            "output": str(result.output) if result.output else None,
            "timestamp": time.time(),
        }
        save_checkpoint(checkpoint, args.checkpoint_file)

        if result.status == "processed" and result.output is not None:
            if args.compress != "none":
                compress_glb(result.output, method=args.compress, logger=logger)  # type: ignore[arg-type]
            logger.info(
                "[%d/%d]   processed (%s)", index, total, format_duration(result.elapsed_seconds)
            )
        elif result.status == "failed":
            logger.error("[%d/%d]   FAILED: %s", index, total, result.reason)
        else:
            logger.info("[%d/%d]   skipped: %s", index, total, result.reason)

        # Incremental manifest — reflects progress after every collection,
        # not just at the very end of the run.
        manifest = generate_manifest(args.output_dir)
        write_manifest(manifest, args.manifest)

    total_elapsed = time.perf_counter() - run_start
    print_summary(results, total_elapsed)
    logger.info(
        "Exporter finished in %s — processed=%d skipped=%d failed=%d",
        format_duration(total_elapsed),
        sum(1 for r in results if r.status == "processed"),
        sum(1 for r in results if r.status == "skipped"),
        sum(1 for r in results if r.status == "failed"),
    )


if __name__ == "__main__":
    main()
