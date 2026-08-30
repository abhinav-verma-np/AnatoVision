"""
Blender-side export script — NOT run with a normal Python interpreter.

Invoked by scripts/model_convert.py as:

    blender --background <file.blend> --python export_blender.py -- <output.glb>

Blender loads <file.blend> as the main file (because of --background
<file.blend>) before running this script, so by the time `main()` runs,
the scene is already populated. This script's only job is to export that
scene to the given output path as .glb and exit — no GUI, no manual steps.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import bpy  # type: ignore[import-not-found]
except ImportError:
    print(
        "export_blender.py must be run inside Blender, e.g.:\n"
        "  blender --background file.blend --python export_blender.py -- output.glb",
        file=sys.stderr,
    )
    sys.exit(1)


def get_script_args() -> list[str]:
    """Blender consumes argv up to '--'; everything after is ours."""
    argv = sys.argv
    if "--" not in argv:
        return []
    return argv[argv.index("--") + 1 :]


def export_to_glb(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        export_apply=True,  # bake modifiers so the export matches the viewport
        export_yup=True,  # glTF convention, matches Three.js / <model-viewer>
        use_selection=False,  # export the whole scene, not just a selection
    )


def main() -> None:
    args = get_script_args()
    if not args:
        print("export_blender.py: missing required output path argument", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args[0])
    export_to_glb(output_path)

    if not output_path.exists():
        print(
            f"export_blender.py: export reported success but {output_path} is missing",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"export_blender.py: wrote {output_path}")


if __name__ == "__main__":
    main()
