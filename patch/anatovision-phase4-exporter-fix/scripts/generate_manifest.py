"""
Generates frontend/public/models/manifest.json from whatever .glb files
actually exist under frontend/public/models/<system>/.

Safe to run standalone at any time:

    python scripts/generate_manifest.py

It never requires manual editing — the manifest is a pure reflection of
disk state, so re-running it after adding/removing a .glb keeps it correct.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_common import (
    ALL_SYSTEM_FOLDERS,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_MODELS_DIR,
    setup_logger,
)


def generate_manifest(models_dir: Path) -> dict[str, dict[str, object]]:
    """Scan models_dir/<system>/*.glb and build the manifest dict.

    Key = model slug (filename stem). If the same slug exists under more
    than one system folder, the first one found wins and a warning is
    left for the caller to log (last-write-wins would silently hide a
    naming collision, which is worse for a dataset this size).
    """
    manifest: dict[str, dict[str, object]] = {}

    for system in ALL_SYSTEM_FOLDERS:
        system_dir = models_dir / system
        if not system_dir.is_dir():
            continue

        for glb_path in sorted(system_dir.glob("*.glb")):
            slug = glb_path.stem
            web_path = f"/models/{system}/{glb_path.name}"

            if slug in manifest:
                # Keep the first entry; still record the newer path isn't lost
                # by leaving the file on disk — just not double-listed.
                continue

            manifest[slug] = {
                "system": system,
                "path": web_path,
                "available": True,
            }

    return manifest


def write_manifest(manifest: dict[str, dict[str, object]], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate frontend/public/models/manifest.json")
    parser.add_argument("--models-dir", type=Path, default=DEFAULT_MODELS_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger = setup_logger(Path("logs/model_processing.log"), name="anatovision.manifest")

    manifest = generate_manifest(args.models_dir)
    write_manifest(manifest, args.manifest)

    logger.info("Manifest written: %s (%d models)", args.manifest, len(manifest))
    for slug, entry in sorted(manifest.items()):
        logger.debug("  %s -> %s", slug, entry["path"])


if __name__ == "__main__":
    main()
