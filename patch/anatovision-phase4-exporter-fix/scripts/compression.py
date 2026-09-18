"""
Compression hooks for exported .glb files.

Real compression (Draco or Meshopt) is delegated to the `gltf-transform`
CLI (npm package @gltf-transform/cli) if it's installed on PATH. This
module never fails the pipeline if that tool is missing — it logs a
notice and leaves the uncompressed .glb in place, which is always a
valid, loadable asset on its own.

    npm install -g @gltf-transform/cli

Usage from process_models.py:

    from compression import compress_glb
    compress_glb(glb_path, method="draco", logger=logger)
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Literal

CompressionMethod = Literal["none", "draco", "meshopt"]

_GLTF_TRANSFORM_SUBCOMMAND: dict[str, str] = {
    "draco": "draco",
    "meshopt": "meshopt",
}


def _find_gltf_transform() -> str | None:
    return shutil.which("gltf-transform")


def compress_glb(
    glb_path: Path,
    method: CompressionMethod,
    logger: logging.Logger | None = None,
) -> bool:
    """Compress a .glb in place using the requested method.

    Returns True if compression was applied, False if it was skipped or
    failed — either way, `glb_path` is left as a valid .glb file.
    """
    log = logger or logging.getLogger("anatovision.pipeline")

    if method == "none":
        return False

    tool = _find_gltf_transform()
    if tool is None:
        log.warning(
            "  compression: gltf-transform not found on PATH — skipping %s "
            "compression, keeping uncompressed GLB (install with "
            "`npm install -g @gltf-transform/cli`)",
            method,
        )
        return False

    subcommand = _GLTF_TRANSFORM_SUBCOMMAND.get(method)
    if subcommand is None:
        log.warning("  compression: unknown method %r — skipping", method)
        return False

    tmp_output = glb_path.with_suffix(".compressed.glb")
    try:
        result = subprocess.run(
            [tool, subcommand, str(glb_path), str(tmp_output)],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("  compression: %s failed to run (%s) — keeping uncompressed GLB", tool, exc)
        tmp_output.unlink(missing_ok=True)
        return False

    if result.returncode != 0 or not tmp_output.exists() or tmp_output.stat().st_size == 0:
        log.warning(
            "  compression: %s %s exited %s — keeping uncompressed GLB. stderr: %s",
            tool,
            subcommand,
            result.returncode,
            result.stderr.strip()[:300],
        )
        tmp_output.unlink(missing_ok=True)
        return False

    tmp_output.replace(glb_path)
    log.info("  compression: applied %s via gltf-transform", method)
    return True
