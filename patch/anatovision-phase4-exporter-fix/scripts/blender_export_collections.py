"""
Blender-side collection exporter — NOT run with a normal Python interpreter.

Invoked by scripts/export_z_anatomy.py as:

    blender --background --factory-startup --app-template Z-Anatomy \
        --python blender_export_collections.py -- \
        <output_dir> <mapping_json> <report_json> <log_file> <force:0|1> \
        <dry_run:0|1> <only_collection_path> <hierarchy_mapping_json> \
        <generate_previews:0|1>

Blender loads the Z-Anatomy application template's startup scene (because
of --app-template) before this script runs, so bpy.context.scene is
already populated with the full anatomical atlas.

Two modes, both handled by this one script:
  - <only_collection_path> == "" : walk the ENTIRE collection hierarchy.
    Used with dry_run=1 by export_z_anatomy.py for the one-time, fast
    "list every collection" pass (no export operator calls happen here,
    so it stays quick even across hundreds of collections). Also runs
    the cross-collection duplicate-output-path check, since only this
    pass has visibility into every collection at once.
  - <only_collection_path> != "" : export exactly ONE named collection.
    This is the normal per-collection export mode — export_z_anatomy.py
    launches one Blender subprocess per collection so a single slow/stuck
    export can never block or take down the whole run.

Permanent project rule: this script never writes to the Z-Anatomy template
itself. It only reads bpy.data / bpy.context and writes derived .glb (and
optional .webp preview) files into AnatoVision's own
frontend/public/models/ tree. Any object visibility changed to include
hidden renderable children is restored before this script exits.
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
    import mathutils  # type: ignore[import-not-found]
except ImportError:
    print(
        "blender_export_collections.py must be run inside Blender, e.g.:\n"
        "  blender --background --factory-startup --app-template Z-Anatomy "
        "--python blender_export_collections.py -- <output_dir> <mapping_json> "
        "<report_json> <log_file> 0 0 '' <hierarchy_mapping_json> 0",
        file=sys.stderr,
    )
    sys.exit(1)


# Heuristic thresholds for export validation. Anatomy models are expected
# to be modeled in meters at roughly life-scale, so these bounds are
# generous on both ends rather than tuned to any one structure's exact
# size — the goal is catching obviously-broken exports (near-zero scale,
# runaway transforms), not policing normal anatomical size variation.
MIN_PLAUSIBLE_DIMENSION_M = 0.0005  # 0.5 mm — below this, likely a scale/transform bug
MAX_PLAUSIBLE_DIMENSION_M = 5.0  # larger than a human body — likely an un-realized transform
MIN_VALID_FILE_SIZE_BYTES = 256  # a well-formed but empty-ish GLB is still bigger than this

PREVIEW_SIZE_PX = 512


def get_script_args() -> list[str]:
    """Blender consumes argv up to '--'; everything after is ours."""
    argv = sys.argv
    if "--" not in argv:
        return []
    return argv[argv.index("--") + 1 :]


# ---------------------------------------------------------------------------
# Collection-aware gathering: instances realized, hidden children included,
# no duplicate objects.
# ---------------------------------------------------------------------------


def _is_collection_instance(obj) -> bool:
    return obj.type == "EMPTY" and obj.instance_type == "COLLECTION" and obj.instance_collection


def gather_export_objects(collection) -> tuple[list, dict]:
    """Collects everything that should be part of this collection's export:
    direct mesh objects, plus collection-instance empties realized into
    real geometry, deduped by object identity. Temporarily un-hides any
    hidden-but-renderable member so it survives export and selection.

    Returns (mesh_objects, restore_state) — restore_state must be passed
    to restore_visibility() after export so the template's hide flags are
    left exactly as found (read-only w.r.t. the template).
    """
    restore_state: dict[str, tuple[bool, bool]] = {}
    seen_names: set[str] = set()
    mesh_objects: list = []
    realized_empties: list = []

    def unhide(obj) -> None:
        if obj.name not in restore_state:
            restore_state[obj.name] = (obj.hide_viewport, obj.hide_get())
        obj.hide_viewport = False
        obj.hide_set(False)

    for obj in collection.objects:
        # Hidden renderable children belong to the exported collection too
        # — un-hide before selection, since a hidden object can't be
        # reliably selected/exported otherwise.
        unhide(obj)

        if obj.type == "MESH":
            if obj.name not in seen_names:
                seen_names.add(obj.name)
                mesh_objects.append(obj)
        elif _is_collection_instance(obj):
            realized_empties.append(obj)

    # Realize collection instances: Blender's own operator converts an
    # instanced-collection reference into real, world-transformed mesh
    # copies. Without this, an instance empty exports as an empty node
    # with no geometry of its own — a direct cause of "broken fragments"
    # for structures authored via instancing (e.g. bilateral symmetry).
    if realized_empties:
        bpy.ops.object.select_all(action="DESELECT")
        for empty in realized_empties:
            empty.select_set(True)
        bpy.context.view_layer.objects.active = realized_empties[0]
        bpy.ops.object.duplicates_make_real(use_base_parent=True, use_hierarchy=True)

        # duplicates_make_real leaves the newly-created real copies
        # selected — collect those as additional mesh objects, deduped.
        for obj in bpy.context.selected_objects:
            unhide(obj)
            if obj.type == "MESH" and obj.name not in seen_names:
                seen_names.add(obj.name)
                mesh_objects.append(obj)

        bpy.ops.object.select_all(action="DESELECT")

    return mesh_objects, restore_state


def restore_visibility(restore_state: dict) -> None:
    for name, (hide_viewport, hidden) in restore_state.items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        obj.hide_viewport = hide_viewport
        obj.hide_set(hidden)


# ---------------------------------------------------------------------------
# Export + validation
# ---------------------------------------------------------------------------


def export_collection_glb(mesh_objects: list, output_path: Path) -> None:
    """Export exactly the given mesh objects as one .glb, preserving world
    transforms and original materials. use_visible=False so a hidden
    object we un-hid moments ago is never silently dropped by the
    exporter's own visibility filter."""
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
        use_visible=False,  # don't re-filter by visibility; we already resolved it
        export_apply=True,  # bake modifiers; does not touch materials
        export_yup=True,
        export_materials="EXPORT",  # preserve original materials, never strip/replace
        export_skins=True,
        export_current_frame=True,
    )

    bpy.ops.object.select_all(action="DESELECT")


def compute_world_bounds(mesh_objects: list):
    """World-space bounding box across all given objects, honoring each
    object's full world transform (not just local geometry)."""
    min_co = mathutils.Vector((float("inf"),) * 3)
    max_co = mathutils.Vector((float("-inf"),) * 3)
    for obj in mesh_objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            min_co.x, min_co.y, min_co.z = (
                min(min_co.x, world_corner.x),
                min(min_co.y, world_corner.y),
                min(min_co.z, world_corner.z),
            )
            max_co.x, max_co.y, max_co.z = (
                max(max_co.x, world_corner.x),
                max(max_co.y, world_corner.y),
                max(max_co.z, world_corner.z),
            )
    return min_co, max_co


def has_broken_transform(mesh_objects: list) -> str | None:
    for obj in mesh_objects:
        m = obj.matrix_world
        for row in m:
            for value in row:
                if value != value or value in (float("inf"), float("-inf")):  # NaN/Inf check
                    return f"non-finite transform value on '{obj.name}'"
        scale = obj.matrix_world.to_scale()
        if any(abs(s) < 1e-8 for s in scale):
            return f"zero (or near-zero) scale on '{obj.name}'"
    return None


def validate_export(output_path: Path, mesh_objects: list) -> tuple[bool, list[str], str]:
    """Returns (passed, warnings, hard_failure_reason).

    Hard failures (empty export, zero geometry, broken transform) mark the
    whole export as failed — the pipeline continues to the next collection
    regardless. Everything else is a warning attached to an otherwise
    "processed" result, so borderline-but-real exports still ship with a
    visible flag in the report rather than being silently dropped.
    """
    warnings: list[str] = []

    total_vertices = sum(len(obj.data.vertices) for obj in mesh_objects if obj.data)
    if total_vertices == 0:
        return False, warnings, "zero-geometry export (no vertices in any mesh object)"

    if not output_path.exists():
        return False, warnings, "export reported success but the GLB file is missing"

    file_size = output_path.stat().st_size
    if file_size < MIN_VALID_FILE_SIZE_BYTES:
        return (
            False,
            warnings,
            (f"exported GLB is suspiciously small ({file_size} bytes) — likely empty"),
        )

    transform_issue = has_broken_transform(mesh_objects)
    if transform_issue:
        return False, warnings, f"broken transform: {transform_issue}"

    min_co, max_co = compute_world_bounds(mesh_objects)
    dims = max_co - min_co
    largest_dim = max(dims.x, dims.y, dims.z)
    smallest_nonzero_dim = min((d for d in (dims.x, dims.y, dims.z) if d > 0), default=0)

    if largest_dim < MIN_PLAUSIBLE_DIMENSION_M:
        return (
            False,
            warnings,
            (
                f"suspiciously tiny bounding box (largest dimension {largest_dim:.6f}m) "
                "— likely a scale or transform bug"
            ),
        )
    if largest_dim > MAX_PLAUSIBLE_DIMENSION_M:
        warnings.append(
            f"extremely large bounding box (largest dimension {largest_dim:.2f}m) "
            "— check for an un-realized or duplicated transform"
        )
    if smallest_nonzero_dim > 0 and (largest_dim / smallest_nonzero_dim) > 500:
        warnings.append(
            f"suspicious bounding box aspect ratio ({largest_dim:.4f}m vs "
            f"{smallest_nonzero_dim:.6f}m) — possible missing geometry on one axis"
        )

    return True, warnings, ""


# ---------------------------------------------------------------------------
# Preview generation: model.glb -> model.webp via Blender background render
# ---------------------------------------------------------------------------


def render_preview(mesh_objects: list, preview_path: Path) -> tuple[bool, str]:
    """Frames the exported mesh objects and renders a single still to
    .webp using Eevee (fast, background-safe). Best-effort: a failure here
    never fails the export itself, only the preview."""
    try:
        preview_path.parent.mkdir(parents=True, exist_ok=True)

        min_co, max_co = compute_world_bounds(mesh_objects)
        center = (min_co + max_co) / 2
        radius = max((max_co - min_co).length / 2, 0.05)

        scene = bpy.context.scene
        cam_data = bpy.data.cameras.new("AnatoVisionPreviewCam")
        cam_obj = bpy.data.objects.new("AnatoVisionPreviewCam", cam_data)
        scene.collection.objects.link(cam_obj)
        cam_obj.location = center + mathutils.Vector((1, -1, 0.6)) * radius * 1.8
        direction = center - cam_obj.location
        cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        cam_data.lens_unit = "FOV"
        cam_data.angle = 0.6  # ~34 degrees, comfortably frames a bounding sphere at this distance
        scene.camera = cam_obj

        light_data = bpy.data.lights.new("AnatoVisionPreviewLight", type="SUN")
        light_data.energy = 3.0
        light_obj = bpy.data.objects.new("AnatoVisionPreviewLight", light_data)
        scene.collection.objects.link(light_obj)
        light_obj.location = cam_obj.location
        light_obj.rotation_euler = cam_obj.rotation_euler

        uses_next_eevee = hasattr(bpy.types, "SceneEEVEE")
        scene.render.engine = "BLENDER_EEVEE_NEXT" if uses_next_eevee else "BLENDER_EEVEE"
        scene.render.resolution_x = PREVIEW_SIZE_PX
        scene.render.resolution_y = PREVIEW_SIZE_PX
        scene.render.image_settings.file_format = "WEBP"
        scene.render.image_settings.quality = 80
        scene.render.filepath = str(preview_path)
        scene.render.film_transparent = True

        bpy.ops.render.render(write_still=True)

        bpy.data.objects.remove(cam_obj, do_unlink=True)
        bpy.data.objects.remove(light_obj, do_unlink=True)
        bpy.data.cameras.remove(cam_data)
        bpy.data.lights.remove(light_data)

        if not preview_path.exists():
            return False, "render.render reported success but no file was written"
        return True, ""
    except Exception as exc:  # noqa: BLE001 - preview failure must never fail the export
        return False, f"preview render failed: {exc}"


# ---------------------------------------------------------------------------
# Hierarchy walk
# ---------------------------------------------------------------------------


def process_collection(
    collection,
    current_path: str,
    top_level_name: str,
    keyword_mapping: dict[str, str],
    hierarchy_mapping: dict[str, tuple[str, ...]],
    output_dir: Path,
    force: bool,
    dry_run: bool,
    generate_previews: bool,
) -> pc.CollectionExportResult | None:
    """Classify + (maybe) export a single collection's complete geometry
    (direct mesh objects + realized instances). Returns None if the
    collection has nothing of its own to export."""
    mesh_objects, restore_state = gather_export_objects(collection)
    if not mesh_objects:
        restore_visibility(restore_state)
        return None

    start = time.perf_counter()
    slug = pc.slugify(collection.name)
    system = pc.classify_hierarchical(
        top_level_name, collection.name, hierarchy_mapping, keyword_mapping
    )
    output_path = output_dir / system / f"{slug}.glb"
    preview_path = output_path.with_suffix(".webp")

    if output_path.exists() and not force:
        restore_visibility(restore_state)
        return pc.CollectionExportResult(
            name=slug,
            collection_path=current_path,
            system=system,
            output=output_path,
            status="skipped",
            reason="already exported (use --force to re-export)",
            elapsed_seconds=time.perf_counter() - start,
            preview=preview_path if preview_path.exists() else None,
        )

    if dry_run:
        restore_visibility(restore_state)
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
        passed, warnings, failure_reason = validate_export(output_path, mesh_objects)

        if not passed:
            output_path.unlink(missing_ok=True)
            restore_visibility(restore_state)
            return pc.CollectionExportResult(
                name=slug,
                collection_path=current_path,
                system=system,
                output=None,
                status="failed",
                reason=failure_reason,
                elapsed_seconds=time.perf_counter() - start,
            )

        preview_ok = False
        preview_reason = ""
        if generate_previews:
            preview_ok, preview_reason = render_preview(mesh_objects, preview_path)
            if not preview_ok:
                warnings.append(f"preview not generated: {preview_reason}")

        restore_visibility(restore_state)
        return pc.CollectionExportResult(
            name=slug,
            collection_path=current_path,
            system=system,
            output=output_path,
            status="processed",
            reason=f"exported {len(mesh_objects)} mesh object(s)",
            elapsed_seconds=time.perf_counter() - start,
            warnings=warnings,
            preview=preview_path if preview_ok else None,
        )
    except Exception as exc:  # noqa: BLE001 - one collection must never abort the run
        output_path.unlink(missing_ok=True)
        restore_visibility(restore_state)
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
    top_level_name: str,
    keyword_mapping: dict[str, str],
    hierarchy_mapping: dict[str, tuple[str, ...]],
    output_dir: Path,
    force: bool,
    dry_run: bool,
    generate_previews: bool,
    parent_path: str,
    results: list[pc.CollectionExportResult],
) -> None:
    """Recursively walk the collection hierarchy. top_level_name is fixed
    at the branch's root and threaded through unchanged — classification
    is based on THAT, never on the concatenated path, so an ancestor's
    name can never leak into an unrelated descendant's system."""
    current_path = f"{parent_path}/{collection.name}" if parent_path else collection.name

    result = process_collection(
        collection,
        current_path,
        top_level_name,
        keyword_mapping,
        hierarchy_mapping,
        output_dir,
        force,
        dry_run,
        generate_previews,
    )
    if result is not None:
        results.append(result)

    for child in collection.children:
        walk_collections(
            child,
            top_level_name,
            keyword_mapping,
            hierarchy_mapping,
            output_dir,
            force,
            dry_run,
            generate_previews,
            current_path,
            results,
        )


def find_collection_by_path(collection_path: str):
    """Resolve a collection by the leaf segment of a 'Parent/Child' path.

    Blender collection names are unique within bpy.data.collections for a
    single local file/template, so a direct name lookup is both correct
    and far cheaper than re-walking the whole hierarchy to find one item.
    """
    leaf_name = collection_path.rsplit("/", 1)[-1]
    return bpy.data.collections.get(leaf_name)


def find_top_level_ancestor_name(target_collection) -> str:
    """Walks down from the scene's root collection to find which
    top-level (first-level-under-root) collection ultimately contains
    target_collection. Returns "" if not found under any top-level
    collection (e.g. the target IS a top-level collection itself, or is
    orphaned)."""
    root = bpy.context.scene.collection

    def search(collection, top_level_name: str) -> str | None:
        if collection is target_collection:
            return top_level_name
        for child in collection.children:
            found = search(child, top_level_name)
            if found is not None:
                return found
        return None

    for top_level in root.children:
        if top_level is target_collection:
            return top_level.name
        found = search(top_level, top_level.name)
        if found is not None:
            return found
    return ""


def check_duplicate_output_paths(results: list[pc.CollectionExportResult]) -> list[str]:
    """Cross-collection check: two different collections computing the
    same output path (system + slug collision) would silently overwrite
    one another. Only meaningful across the full listing pass."""
    seen: dict[Path, str] = {}
    duplicates: list[str] = []
    for r in results:
        if r.output is None:
            continue
        if r.output in seen:
            duplicates.append(
                f"Duplicate output path {r.output}: claimed by both "
                f"'{seen[r.output]}' and '{r.collection_path}'"
            )
        else:
            seen[r.output] = r.collection_path
    return duplicates


def main() -> None:
    args = get_script_args()
    if len(args) < 9:
        print(
            "blender_export_collections.py: expected 9 args: "
            "<output_dir> <mapping_json> <report_json> <log_file> <force:0|1> "
            "<dry_run:0|1> <only_collection_path> <hierarchy_mapping_json> "
            "<generate_previews:0|1>",
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
    hierarchy_mapping_path = Path(args[7])
    generate_previews = args[8] == "1"

    logger = pc.setup_logger(log_path, name="anatovision.blender")
    pc.ensure_output_dirs(output_dir)
    keyword_mapping = pc.load_model_mapping(mapping_path)
    hierarchy_mapping = pc.load_system_hierarchy_mapping(hierarchy_mapping_path)

    results: list[pc.CollectionExportResult] = []

    if only_collection_path:
        # Single-collection export mode — one subprocess, one collection.
        collection = find_collection_by_path(only_collection_path)
        if collection is None:
            results.append(
                pc.CollectionExportResult(
                    name=pc.slugify(only_collection_path.rsplit("/", 1)[-1]),
                    collection_path=only_collection_path,
                    system=pc.UNCLASSIFIED,
                    output=None,
                    status="failed",
                    reason=f"collection not found in template: {only_collection_path}",
                )
            )
        else:
            top_level_name = find_top_level_ancestor_name(collection) or collection.name
            result = process_collection(
                collection,
                only_collection_path,
                top_level_name,
                keyword_mapping,
                hierarchy_mapping,
                output_dir,
                force,
                dry_run,
                generate_previews,
            )
            if result is not None:
                results.append(result)
            else:
                results.append(
                    pc.CollectionExportResult(
                        name=pc.slugify(collection.name),
                        collection_path=only_collection_path,
                        system=pc.classify_hierarchical(
                            top_level_name, collection.name, hierarchy_mapping, keyword_mapping
                        ),
                        output=None,
                        status="failed",
                        reason="collection has no mesh objects to export",
                    )
                )
    else:
        # Full-atlas listing/walk mode.
        logger.info("[blender] Loaded %d classification keywords", len(keyword_mapping))
        logger.info("[blender] Loaded %d hierarchy system mappings", len(hierarchy_mapping))
        logger.info("[blender] Traversing Z-Anatomy collections in the active scene…")

        root_collection = bpy.context.scene.collection
        for top_level in root_collection.children:
            walk_collections(
                top_level,
                top_level.name,
                keyword_mapping,
                hierarchy_mapping,
                output_dir,
                force,
                dry_run,
                generate_previews,
                "",
                results,
            )

        # The scene's own root collection can (rarely) hold loose mesh
        # objects directly, outside any named sub-collection.
        root_meshes = [obj for obj in root_collection.objects if obj.type == "MESH"]
        if root_meshes:
            walk_collections(
                root_collection,
                root_collection.name,
                keyword_mapping,
                hierarchy_mapping,
                output_dir,
                force,
                dry_run,
                generate_previews,
                "",
                results,
            )

        duplicate_issues = check_duplicate_output_paths(results)
        for issue in duplicate_issues:
            logger.warning("[blender] %s", issue)

    for r in results:
        if r.status == "processed":
            warn_suffix = f" ({len(r.warnings)} warning(s))" if r.warnings else ""
            logger.info(
                "[blender]   processed: %s -> %s [%s]%s",
                r.collection_path,
                r.output,
                r.system,
                warn_suffix,
            )
            for w in r.warnings:
                logger.warning("[blender]     warning: %s", w)
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
