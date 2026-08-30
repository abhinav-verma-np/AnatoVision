"""
Blender-side collection exporter — NOT run with a normal Python interpreter.

Invoked by scripts/export_z_anatomy.py as:

    blender --background --factory-startup --app-template Z-Anatomy \\
        --python blender_export_collections.py -- \\
        <output_dir> <mapping_json> <report_json> <log_file> <force:0|1> \\
        <dry_run:0|1> <only_collection_path>

Blender loads the Z-Anatomy application template's startup scene (because
of --app-template) before this script runs, so bpy.context.scene is
already populated with the full anatomical atlas.

Two modes, both handled by this one script:
  - <only_collection_path> == "" : walk the ENTIRE collection hierarchy.
    Used with dry_run=1 by export_z_anatomy.py for the one-time, fast
    "list every collection" pass (no export operator calls happen here,
    so it stays quick even across hundreds of collections).
  - <only_collection_path> != "" : export exactly ONE named collection.
    This is the normal per-collection export mode — export_z_anatomy.py
    launches one Blender subprocess per collection so a single slow/stuck
    export can never block or take down the whole run.

Permanent project rule: this script never writes to the Z-Anatomy template
itself. It only reads bpy.data / bpy.context and writes derived .glb files
into AnatoVision's own frontend/public/models/ tree.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Make sibling modules importable regardless of Blender's default sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pipeline_common as pc  # noqa: E402

try:
    import bpy  # type: ignore[import-not-found]
except ImportError:
    print(
        "blender_export_collections.py must be run inside Blender, e.g.:\n"
        "  blender --background --factory-startup --app-template Z-Anatomy "
        "--python blender_export_collections.py -- <output_dir> <mapping_json> "
        "<report_json> <log_file> 0 0 ''",
        file=sys.stderr,
    )
    sys.exit(1)


def get_script_args() -> list[str]:
    """Blender consumes argv up to '--'; everything after is ours."""
    argv = sys.argv
    if "--" not in argv:
        return []
    return argv[argv.index("--") + 1 :]


def export_collection_glb(mesh_objects: list, output_path: Path) -> None:
    """Export exactly the given mesh objects as one .glb, leaving every
    other object in the scene untouched (read-only w.r.t. the template)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects:
        obj.select_set(True)
    if bpy.context.view_layer.objects.active is None and mesh_objects:
        bpy.context.view_layer.objects.active = mesh_objects[0]

    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
    )

    bpy.ops.object.select_all(action="DESELECT")


def process_collection(
    collection,
    current_path: str,
    mapping: dict[str, str],
    output_dir: Path,
    force: bool,
    dry_run: bool,
) -> pc.CollectionExportResult | None:
    """Classify + (maybe) export a single collection's direct mesh objects.

    Returns None if the collection has no mesh objects of its own (nothing
    to export there — still a valid, non-error outcome during a walk).
    """
    mesh_objects = [obj for obj in collection.objects if obj.type == "MESH"]
    if not mesh_objects:
        return None

    start = time.perf_counter()
    slug = pc.slugify(collection.name)
    system = pc.classify_model(current_path, mapping)
    output_path = output_dir / system / f"{slug}.glb"

    if output_path.exists() and not force:
        return pc.CollectionExportResult(
            name=slug,
            collection_path=current_path,
            system=system,
            output=output_path,
            status="skipped",
            reason="already exported (use --force to re-export)",
            elapsed_seconds=time.perf_counter() - start,
        )

    if dry_run:
        return pc.CollectionExportResult(
            name=slug,
            collection_path=current_path,
            system=system,
            output=output_path,
            status="skipped",
            reason="dry run",
            elapsed_seconds=time.perf_counter() - start,
        )

    try:
        export_collection_glb(mesh_objects, output_path)
        if not output_path.exists():
            raise RuntimeError("glTF export reported success but wrote no file")
        return pc.CollectionExportResult(
            name=slug,
            collection_path=current_path,
            system=system,
            output=output_path,
            status="processed",
            reason=f"exported {len(mesh_objects)} mesh object(s)",
            elapsed_seconds=time.perf_counter() - start,
        )
    except Exception as exc:  # noqa: BLE001 - one collection must never abort the run
        output_path.unlink(missing_ok=True)
        return pc.CollectionExportResult(
            name=slug,
            collection_path=current_path,
            system=system,
            output=None,
            status="failed",
            reason=f"Blender export failed: {exc}",
            elapsed_seconds=time.perf_counter() - start,
        )


def walk_collections(
    collection,
    mapping: dict[str, str],
    output_dir: Path,
    force: bool,
    dry_run: bool,
    parent_path: str,
    results: list[pc.CollectionExportResult],
) -> None:
    """Recursively walk the collection hierarchy, exporting each collection
    that directly owns mesh objects, and continuing into children
    regardless (preserves hierarchy — a parent group and its own leaf
    geometry can both produce assets). Used only for the full-atlas
    listing pass (dry_run=1, only_collection="")."""
    current_path = f"{parent_path}/{collection.name}" if parent_path else collection.name

    result = process_collection(collection, current_path, mapping, output_dir, force, dry_run)
    if result is not None:
        results.append(result)

    for child in collection.children:
        walk_collections(child, mapping, output_dir, force, dry_run, current_path, results)


def find_collection_by_path(collection_path: str):
    """Resolve a collection by the leaf segment of a 'Parent/Child' path.

    Blender collection names are unique within bpy.data.collections for a
    single local file/template, so a direct name lookup is both correct
    and far cheaper than re-walking the whole hierarchy to find one item.
    """
    leaf_name = collection_path.rsplit("/", 1)[-1]
    return bpy.data.collections.get(leaf_name)


def main() -> None:
    args = get_script_args()
    if len(args) < 7:
        print(
            "blender_export_collections.py: expected 7 args: "
            "<output_dir> <mapping_json> <report_json> <log_file> <force:0|1> "
            "<dry_run:0|1> <only_collection_path>",
            file=sys.stderr,
        )
        sys.exit(1)

    output_dir = Path(args[0])
    mapping_path = Path(args[1])
    report_path = Path(args[2])
    log_path = Path(args[3])
    force = args[4] == "1"
    dry_run = args[5] == "1"
    only_collection_path = args[6]

    logger = pc.setup_logger(log_path, name="anatovision.blender")
    pc.ensure_output_dirs(output_dir)
    mapping = pc.load_model_mapping(mapping_path)

    results: list[pc.CollectionExportResult] = []

    if only_collection_path:
        # Single-collection export mode — one subprocess, one collection.
        collection = find_collection_by_path(only_collection_path)
        if collection is None:
            results.append(
                pc.CollectionExportResult(
                    name=pc.slugify(only_collection_path.rsplit("/", 1)[-1]),
                    collection_path=only_collection_path,
                    system=pc.classify_model(only_collection_path, mapping),
                    output=None,
                    status="failed",
                    reason=f"collection not found in template: {only_collection_path}",
                )
            )
        else:
            result = process_collection(
                collection, only_collection_path, mapping, output_dir, force, dry_run
            )
            if result is not None:
                results.append(result)
            else:
                results.append(
                    pc.CollectionExportResult(
                        name=pc.slugify(collection.name),
                        collection_path=only_collection_path,
                        system=pc.classify_model(only_collection_path, mapping),
                        output=None,
                        status="failed",
                        reason="collection has no mesh objects to export",
                    )
                )
    else:
        # Full-atlas listing/walk mode.
        logger.info("[blender] Loaded %d classification keywords", len(mapping))
        logger.info("[blender] Traversing Z-Anatomy collections in the active scene…")

        root_collection = bpy.context.scene.collection
        for top_level in root_collection.children:
            walk_collections(top_level, mapping, output_dir, force, dry_run, "", results)

        # The scene's own root collection can (rarely) hold loose mesh
        # objects directly, outside any named sub-collection.
        root_meshes = [obj for obj in root_collection.objects if obj.type == "MESH"]
        if root_meshes:
            walk_collections(root_collection, mapping, output_dir, force, dry_run, "", results)

    for r in results:
        if r.status == "processed":
            logger.info(
                "[blender]   processed: %s -> %s [%s]", r.collection_path, r.output, r.system
            )
        elif r.status == "skipped":
            logger.info("[blender]   skipped: %s (%s)", r.collection_path, r.reason)
        else:
            logger.error("[blender]   FAILED: %s (%s)", r.collection_path, r.reason)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)

    logger.info("[blender] Wrote report: %s (%d collection(s))", report_path, len(results))


if __name__ == "__main__":
    main()
