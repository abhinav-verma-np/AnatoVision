"""
Converts a single source model file into a .glb.

- .blend  -> Blender in background mode, running export_blender.py
- .glb    -> already the target format, copied as-is
- .gltf/.obj/.fbx/.stl -> trimesh (pure-Python, no Blender required)

Every conversion function returns (success, message) and never raises —
process_models.py relies on that to keep going after a single failed
model instead of crashing the whole run.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pipeline_common import DEFAULT_EXPORT_SCRIPT

BLENDER_TIMEOUT_SECONDS = 600

try:
    import trimesh  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - exercised only when dep is missing
    trimesh = None


def convert_to_glb(
    input_path: Path,
    output_path: Path,
    blender_exe: str = "blender",
) -> tuple[bool, str]:
    """Dispatch to the right converter based on file extension."""
    suffix = input_path.suffix.lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if suffix == ".blend":
        return _convert_via_blender(input_path, output_path, blender_exe)
    if suffix == ".glb":
        return _copy_glb(input_path, output_path)
    if suffix in {".gltf", ".obj", ".fbx", ".stl"}:
        return _convert_via_trimesh(input_path, output_path)
    return False, f"unsupported extension: {suffix}"


def _copy_glb(input_path: Path, output_path: Path) -> tuple[bool, str]:
    try:
        shutil.copy2(input_path, output_path)
    except OSError as exc:
        return False, f"failed to copy .glb: {exc}"
    return True, "copied (already .glb)"


def _convert_via_blender(
    input_path: Path,
    output_path: Path,
    blender_exe: str,
) -> tuple[bool, str]:
    resolved = shutil.which(blender_exe) or blender_exe

    command = [
        resolved,
        "--background",
        str(input_path),
        "--python",
        str(DEFAULT_EXPORT_SCRIPT),
        "--",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=BLENDER_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return False, (
            f"Blender executable not found ('{blender_exe}'). Install Blender "
            "and ensure it's on PATH, or pass --blender-exe / set BLENDER_EXE."
        )
    except subprocess.TimeoutExpired:
        return False, f"Blender export timed out after {BLENDER_TIMEOUT_SECONDS}s"

    if result.returncode != 0 or not output_path.exists():
        stderr_tail = (result.stderr or "").strip()[-500:]
        return False, f"Blender export failed (exit {result.returncode}): {stderr_tail}"

    return True, "exported via Blender CLI"


def _convert_via_trimesh(input_path: Path, output_path: Path) -> tuple[bool, str]:
    if trimesh is None:
        return False, (
            "trimesh is not installed — run `pip install -r scripts/requirements.txt` "
            "to convert .obj/.fbx/.stl/.gltf files without Blender"
        )

    try:
        scene = trimesh.load(str(input_path), force="scene")
        scene.export(str(output_path), file_type="glb")
    except Exception as exc:  # noqa: BLE001 - any conversion failure must not crash the pipeline
        return False, f"trimesh conversion failed: {exc}"

    if not output_path.exists() or output_path.stat().st_size == 0:
        return False, "trimesh reported success but produced no output file"

    return True, "converted via trimesh"
