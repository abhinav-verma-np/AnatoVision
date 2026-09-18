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

Export granularity — the core fix in this version:
Z-Anatomy nests real anatomical structures several collections deep, e.g.

    Skeletal system > Cranium > Bones of cranium > Frontal bone
        > mesh objects
        > Squamous part
        > Nasal part
        > Orbital part
        > Sinus of frontal bone

"Frontal bone" is the LOWEST MEANINGFUL anatomical collection — the first
one (walking down) that owns mesh objects directly. Its child collections
(Squamous part, Nasal part, ...) are fragments of the SAME structure, not
separate structures, and must be ABSORBED into one combined "Frontal
bone" export rather than exported as their own siblings. Purely
organizational children (e.g. "External surface of frontal bone") own no
real geometry of their own and must never be independently exported —
they are detected by name pattern and reported as Skipped, not Failed.

Two modes, both handled by this one script:
  - <only_collection_path> == "" : walk the ENTIRE collection hierarchy,
    finding every export boundary and skip point. Used with dry_run=1 by
    export_z_anatomy.py for the one-time "list everything" pass (no
    export operator calls happen here, so it stays fast). Also runs the
    cross-collection duplicate-output-path check.
  - <only_collection_path> != "" : export exactly ONE boundary collection
    (already identified as such by the listing pass) — export_z_anatomy.py
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
import re
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

# Purely organizational / labeling collections that own no real anatomy of
# their own — e.g. "External surface of frontal bone", "Orbital surface of
# X", annotation/label groupings. These are detected by name BEFORE any
# export is attempted, and are reported as Skipped, never Failed. This is
# a safety net alongside (not instead of) the structural "lowest
# meaningful collection" rule below — the structural rule already stops
# Blender from ever independently visiting most of these (they're
# descendants of an already-decided boundary), but a name match still
# takes priority in case one appears somewhere the structural rule alone
# wouldn't catch (e.g. as a sibling rather than a descendant).
ORGANIZATIONAL_NAME_PATTERNS = [
    re.compile(r"\bsurface\s+of\b", re.IGNORECASE),
    re.compile(
        r"^(external|internal|anterior|posterior|medial|lateral|superior|inferior|orbital)"
        r"\s+surface\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bsurfaces?\s+of\s+the\b", re.IGNORECASE),
    re.compile(r"\bannotations?\b", re.IGNORECASE),
    re.compile(r"\blabels?\b", re.IGNORECASE),
    re.compile(r"\btext\s+labels?\b", re.IGNORECASE),
]


def is_organizational_collection(name: str) -> bool:
    return any(pattern.search(name) for pattern in ORGANIZATIONAL_NAME_PATTERNS)


def get_script_args() -> list[str]:
    """Blender consumes argv up to '--'; everything after is ours."""
    argv = sys.argv
    if "--" not in argv:
        return []
    return argv[argv.index("--") + 1 :]


# ---------------------------------------------------------------------------
# Object gathering: instances realized, hidden children included, no
# duplicate objects. Two layers:
#   - gather_direct_objects_with_instances: ONE collection's own members.
#   - gather_all_descendant_meshes: recursively absorbs an entire subtree
#     once a boundary has been decided (see find_export_boundaries).
# ---------------------------------------------------------------------------


def _is_collection_instance(obj) -> bool:
    return obj.type == "EMPTY" and obj.instance_type == "COLLECTION" and obj.instance_collection


def log_material_state(stage: str, label: str, objects: list) -> None:
    """Requirements 1-2: instrumentation checkpoint. Prints a one-line,
    grep-able report of material presence for `objects` at a named
    pipeline stage, so Evidence-First debugging (console/PowerShell logs)
    can show exactly where a structure's material slots disappeared:
    before realization, after duplicates_make_real, after
    make_single_user, after join, or before GLB export."""
    total = len(objects)
    with_material = sum(
        1
        for obj in objects
        if obj.material_slots and any(slot.material is not None for slot in obj.material_slots)
    )
    print(f"[materials:{stage}] {label}: {with_material}/{total} object(s) have a material assigned")


def gather_direct_objects_with_instances(collection) -> tuple[list, dict]:
    """Collects this ONE collection's direct mesh objects, realizing any
    collection-instance empties into real geometry, deduped by name.
    Temporarily un-hides any hidden-but-renderable member so it survives
    selection and export.

    Returns (mesh_objects, restore_state) — restore_state must be passed
    to restore_visibility() once the whole export boundary is done, so
    the template's hide flags are left exactly as found.
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

    log_material_state("before realization", collection.name, mesh_objects)

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

        log_material_state("after duplicates_make_real", collection.name, mesh_objects)

    return mesh_objects, restore_state


def gather_all_descendant_meshes(
    collection, visited: set[str] | None = None
) -> tuple[list, list[str], dict]:
    """Once a collection has been decided as an export boundary (it owns
    direct mesh objects), this absorbs EVERY descendant collection's
    geometry into that one boundary — this is what turns "Frontal bone"
    plus its Squamous/Nasal/Orbital/Sinus children into ONE combined
    export instead of five fragments.

    Organizational sub-collections encountered along the way (by name)
    are still walked into (in case something real is nested even deeper)
    but are recorded separately so the caller can emit visible Skipped
    entries for them in the report, rather than silently swallowing them.

    `visited`: Blender's collection hierarchy is a DAG, not a strict tree
    — the same collection (e.g. "Bonus collection") can be linked under
    more than one parent. Callers pass in a single set shared across the
    whole run (see find_export_boundaries) so a multiply-linked
    collection is consumed exactly once instead of contributing duplicate
    geometry to two different exports, or being walked twice here. If no
    set is passed, one is created locally (still dedupes within this one
    absorption call).

    Returns (mesh_objects, organizational_names_encountered, restore_state).
    """
    all_meshes: list = []
    seen_names: set[str] = set()
    organizational_names: list[str] = []
    restore_state: dict[str, tuple[bool, bool]] = {}
    if visited is None:
        visited = set()

    def walk(coll) -> None:
        if coll.name in visited:
            return
        visited.add(coll.name)

        if is_organizational_collection(coll.name):
            organizational_names.append(coll.name)

        objs, restore = gather_direct_objects_with_instances(coll)
        restore_state.update(restore)
        for obj in objs:
            if obj.name not in seen_names:
                seen_names.add(obj.name)
                all_meshes.append(obj)

        for child in coll.children:
            walk(child)

    for child in collection.children:
        walk(child)

    return all_meshes, organizational_names, restore_state


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


_MATERIAL_GID_ATTR = "amv_material_gid"


def _build_global_material_list(mesh_objects: list) -> tuple[list, dict]:
    """Builds ONE de-duplicated, order-preserving list of every distinct
    material (by name — Blender guarantees unique names within
    bpy.data.materials, so name is a safe, simple identity key) used
    across every object about to be joined. None (an intentionally empty
    slot) is included as its own entry so a face that genuinely had no
    material keeps that state rather than being forced onto some other
    material. Returns (global_materials, name_to_gid)."""
    global_materials: list = []
    name_to_gid: dict[str, int] = {}
    for obj in mesh_objects:
        for slot in obj.material_slots:
            mat = slot.material
            key = mat.name if mat is not None else "__none__"
            if key not in name_to_gid:
                name_to_gid[key] = len(global_materials)
                global_materials.append(mat)
    return global_materials, name_to_gid


def _tag_faces_with_global_material_id(obj, name_to_gid: dict) -> None:
    """Writes a custom per-face integer attribute recording, for every
    polygon, the GLOBAL material id (an index into the list built by
    _build_global_material_list) it currently uses. Custom mesh
    attributes are concatenated alongside the geometry itself by
    bpy.ops.object.join(), so this value travels WITH each face through
    the join — giving preserve_materials_after_join a way to recover
    exactly which material every face originally had that does NOT
    depend on the join operator's internal, undocumented ordering of the
    objects it merges."""
    mesh = obj.data
    attr = mesh.attributes.get(_MATERIAL_GID_ATTR)
    if attr is None:
        attr = mesh.attributes.new(_MATERIAL_GID_ATTR, type="INT", domain="FACE")

    slots = obj.material_slots
    for poly in mesh.polygons:
        mat = slots[poly.material_index].material if poly.material_index < len(slots) else None
        key = mat.name if mat is not None else "__none__"
        attr.data[poly.index].value = name_to_gid.get(key, -1)


def preserve_materials_before_join(mesh_objects: list) -> tuple[list[str], list]:
    """Requirements 1-3: before bpy.ops.object.join() ever runs on more
    than one object, guarantee every one of them owns fully independent
    (single-user) mesh AND material data, AND tag every face with a
    global material id that survives the join regardless of what
    bpy.ops.object.join() itself does to material slots.

    THE EXACT OPERATION THAT WAS LOSING MATERIAL SLOTS (requirement 1):
    this function used to build the global material list and tag every
    object's faces BEFORE running make_single_user. duplicates_make_real
    produces LINKED duplicates that keep SHARING one mesh data-block
    across several objects with DIFFERENT per-instance materials — true
    of most bilateral/symmetric structures here (Axial skeleton,
    Peripheral nervous system, etc.). _tag_faces_with_global_material_id
    writes its custom attribute onto obj.data. When a second object
    shares that same data-block, its tagging call finds the attribute the
    first object just wrote and OVERWRITES it with its own, different
    per-object material lookup — last object processed wins, silently
    destroying every earlier sharer's tag before the data is ever split
    apart. make_single_user then faithfully duplicates that already-
    corrupted shared data into each object's own copy, and
    preserve_materials_after_join rebuilds a correct-looking slot table
    from already-wrong (or out-of-range) tags — which is exactly why
    Axial skeleton.j, Deltoid muscle.j, Left lung.j, and Peripheral
    nervous system.j still came out with no material assigned even with
    the tag-and-rebuild safety net in place.

    THE FIX: separate the data first, tag second. make_single_user runs
    BEFORE _build_global_material_list/_tag_faces_with_global_material_id
    are ever called, so every object already owns its own exclusive mesh
    data by the time anything writes a tag onto it — nothing else can
    share, and therefore nothing else can overwrite, that attribute.
    object=True is deliberately omitted: it targets object-level
    multi-collection membership, which has nothing to do with mesh/
    material independence, and risks Blender substituting a different
    Object data-block than the one this function (and its caller) already
    hold references to and read obj.material_slots/obj.data from moments
    later.

    Returns (warnings, global_materials) — global_materials must be
    passed to preserve_materials_after_join once the join has happened.
    """
    if len(mesh_objects) < 2:
        return [], []

    original_slot_counts = {obj.name: len(obj.material_slots) for obj in mesh_objects}

    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objects[0]

    # Separate any shared mesh/material data FIRST — see docstring above.
    bpy.ops.object.make_single_user(type="SELECTED_OBJECTS", obdata=True, material=True)

    log_material_state("after make_single_user", mesh_objects[0].name, mesh_objects)

    warnings: list[str] = []
    for obj in mesh_objects:
        before = original_slot_counts.get(obj.name, 0)
        after = len(obj.material_slots)
        if after != before:
            warnings.append(
                f"{obj.name}: material slot count changed from {before} to "
                f"{after} during single-user duplication — check for lost materials"
            )

    # Only now, with every object owning exclusive mesh data, tag each
    # object's faces with a global material id. Tagging any earlier would
    # risk exactly the shared-data overwrite described above.
    global_materials, name_to_gid = _build_global_material_list(mesh_objects)
    for obj in mesh_objects:
        _tag_faces_with_global_material_id(obj, name_to_gid)

    return warnings, global_materials


def preserve_materials_after_join(joined_obj, global_materials: list) -> list[str]:
    """Requirement 3: rebuild the joined object's material slot table from
    the original objects, using the per-face global-material-id attribute
    _tag_faces_with_global_material_id wrote BEFORE the join (which
    survives bpy.ops.object.join() alongside the geometry itself,
    independent of the order Blender internally merges objects in).

    Sets joined_obj.data.materials to exactly `global_materials`
    (rebuilding the slot table itself), then walks every polygon and
    restores its correct material_index from the tagged attribute — so
    both the slot table AND each face's actual assignment are restored,
    not just an empty slot list that happens to contain the right
    materials with every face pointing at slot 0 (which would still
    render wrong, just no longer literally "no material").

    Returns a list of warnings (requirement 4: never silently export a
    white model) for anything that couldn't be recovered — e.g. a face
    whose tag is missing, which should never happen but must be reported
    rather than silently ignored if it does.
    """
    warnings: list[str] = []
    if not global_materials:
        return warnings

    mesh = joined_obj.data

    mesh.materials.clear()
    for mat in global_materials:
        mesh.materials.append(mat)

    attr = mesh.attributes.get(_MATERIAL_GID_ATTR)
    if attr is None:
        warnings.append(
            f"{joined_obj.name}: no per-face material tag survived the join — "
            "material slot table was rebuilt but per-face assignment could not be restored"
        )
        return warnings

    missing_faces = 0
    for poly in mesh.polygons:
        gid = attr.data[poly.index].value
        if 0 <= gid < len(global_materials):
            poly.material_index = gid
        else:
            missing_faces += 1

    if missing_faces:
        warnings.append(
            f"{joined_obj.name}: {missing_faces} face(s) had no valid material tag "
            "after join — those faces may render with the wrong or no material"
        )

    mesh.attributes.remove(attr)
    return warnings


def check_material_presence(mesh_objects: list) -> list[str]:
    """Requirements 8-9: called immediately before the GLB is written.
    If an object comes out of gathering/joining with zero material slots,
    or every slot is empty, that structure is about to export as flat
    default white with no signal anywhere that anything went wrong. This
    turns that into an explicit, visible warning on the export result
    instead of a silent white mesh."""
    warnings: list[str] = []
    for obj in mesh_objects:
        slots = obj.material_slots
        if not slots or not any(slot.material is not None for slot in slots):
            warnings.append(
                f"{obj.name}: exported with no material assigned — "
                "will render as a flat/default material"
            )
    return warnings


def export_collection_glb(mesh_objects: list, output_path: Path) -> tuple[list, list[str]]:
    """Export exactly the given mesh objects as one .glb, preserving world
    transforms and original materials (Principled BSDF base colors,
    vertex colors, and image texture links all live on the mesh/material
    data-blocks this function never rebuilds or strips — only ever
    duplicates via preserve_materials_before_join, or restores via
    preserve_materials_after_join).

    When more than one mesh object is given (a boundary's own direct
    objects plus everything absorbed from its descendants), they are
    JOINED into a single object before export, so one meaningful
    anatomical collection always lands in the GLB as one clean mesh
    rather than a scattering of separate nodes. Joining is destructive
    (Blender deletes every object but one), so preserve_materials_before_join
    always runs first to make every object's mesh and material data
    single-user AND tag every face with a global material id, and
    preserve_materials_after_join always runs immediately after join() to
    rebuild the resulting object's material slot table and per-face
    assignment from that tag — real Blender evidence showed join can drop
    material slots even after single-user duplication, so the tag-and-
    rebuild step is the actual fix, not single-user alone.

    Five instrumentation checkpoints (requirements 1-2) print material
    presence to the console/log at each stage material slots could be
    lost: before realization and after duplicates_make_real (both inside
    gather_direct_objects_with_instances), after make_single_user (inside
    preserve_materials_before_join), and after join / before GLB export
    (both here).

    use_visible=False so a hidden object we un-hid moments ago is never
    silently dropped by the exporter's own visibility filter.

    export_materials="EXPORT" tells Blender's glTF exporter to embed
    materials (base color, textures, vertex colors) directly in the GLB
    rather than stripping or referencing them externally.

    Before writing the GLB, check_material_presence verifies every final
    object still has at least one real material slot (requirement 8) and
    surfaces a warning — never a silent white export — for any that
    don't (requirement 9).

    Returns (final_objects, warnings):
      - final_objects: a single joined object when more than one was
        given, otherwise the original list unchanged. Callers MUST use
        this for anything done after export (bounds/validation,
        previews): join deletes every object but one, so the objects
        originally passed in are no longer all valid.
      - warnings: material-related warnings collected along the way,
        meant to be merged into the caller's existing validation warnings.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects:
        obj.select_set(True)
    if mesh_objects:
        bpy.context.view_layer.objects.active = mesh_objects[0]

    warnings: list[str] = []
    final_objects = mesh_objects
    if len(mesh_objects) > 1:
        pre_warnings, global_materials = preserve_materials_before_join(mesh_objects)
        warnings.extend(pre_warnings)

        bpy.ops.object.join()
        final_objects = [bpy.context.view_layer.objects.active]
        log_material_state("after join", final_objects[0].name, final_objects)

        warnings.extend(preserve_materials_after_join(final_objects[0], global_materials))

    log_material_state(
        "before GLB export",
        final_objects[0].name if final_objects else output_path.stem,
        final_objects,
    )
    warnings.extend(check_material_presence(final_objects))

    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        use_selection=True,
        use_visible=False,  # don't re-filter by visibility; we already resolved it
        export_apply=True,  # bake modifiers (evaluated geometry); does not touch materials
        export_yup=True,
        export_materials="EXPORT",  # preserve original materials, never strip/replace
        export_skins=True,
        export_current_frame=True,
    )

    bpy.ops.object.select_all(action="DESELECT")
    return final_objects, warnings




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
    "processed" result.
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

        # Pinned per project spec: Blender 5.2, BLENDER_EEVEE.
        scene.render.engine = "BLENDER_EEVEE"
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
# Export boundary resolution
# ---------------------------------------------------------------------------


def export_boundary(
    collection,
    current_path: str,
    top_level_name: str,
    all_meshes: list,
    keyword_mapping: dict[str, str],
    hierarchy_mapping: dict[str, tuple[str, ...]],
    output_dir: Path,
    force: bool,
    dry_run: bool,
    generate_previews: bool,
) -> pc.CollectionExportResult:
    """Exports one already-decided boundary collection's fully-absorbed
    mesh set (its own direct objects + everything recursively gathered
    from its descendants) as ONE combined .glb. Shared by both the
    full-walk mode and the single-collection subprocess mode so the two
    can never disagree about what a boundary export actually contains."""
    start = time.perf_counter()
    slug = pc.slugify(collection.name)
    system = pc.classify_hierarchical(
        top_level_name, collection.name, hierarchy_mapping, keyword_mapping
    )
    output_path = output_dir / system / f"{slug}.glb"
    preview_path = output_path.with_suffix(".webp")

    if output_path.exists() and not force:
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
        exported_objects, material_warnings = export_collection_glb(all_meshes, output_path)
        passed, warnings, failure_reason = validate_export(output_path, exported_objects)
        warnings = material_warnings + warnings

        if not passed:
            output_path.unlink(missing_ok=True)
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
        if generate_previews:
            preview_ok, preview_reason = render_preview(exported_objects, preview_path)
            if not preview_ok:
                warnings.append(f"preview not generated: {preview_reason}")

        return pc.CollectionExportResult(
            name=slug,
            collection_path=current_path,
            system=system,
            output=output_path,
            status="processed",
            reason=f"exported {len(all_meshes)} mesh object(s), absorbing all descendants",
            elapsed_seconds=time.perf_counter() - start,
            warnings=warnings,
            preview=preview_path if preview_ok else None,
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


def find_export_boundaries(
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
    visited: set[str],
) -> None:
    """Walks the hierarchy top-down looking for export boundaries.

    Scene Collection (the scene's root/master collection) and numbered
    system roots (its direct children, e.g. "1 Skeletal system") are
    always traversal-only — see below — regardless of any direct meshes
    they hold.

    A collection is a boundary — "the lowest meaningful anatomical
    collection" — the moment it owns any DIRECT mesh objects of its own.
    At that point every descendant collection's geometry is absorbed into
    ONE combined export and the walk does NOT continue into those
    children as separate export candidates (this is what turns Frontal
    bone + Squamous/Nasal/Orbital/Sinus into one GLB instead of five).

    A collection matching an organizational name pattern is recorded as
    Skipped and the walk continues into its children defensively, but it
    is never itself treated as an export target.

    A collection with neither direct meshes nor organizational-name
    status is a pure pass-through grouping node (e.g. "Bones of cranium")
    — the walk continues into its children to find their own boundaries.
    Scene Collection and every numbered system root are forced into this
    same pass-through path regardless of direct meshes, so the walk
    always continues down to the actual lowest meaningful anatomical
    collection instead of stopping at a whole system.

    `visited` is a single set shared for the entire run (created once in
    main() and threaded through every call, including into
    gather_all_descendant_meshes). Blender's collection hierarchy is a
    DAG, not a strict tree — a collection can be linked under more than
    one parent (this is the confirmed cause of the duplicate-traversal
    bug through "Scene Collection" and "Bonus collection"). Every
    collection this function is invoked on — organizational, boundary,
    or pass-through — is checked against `visited` first and skipped
    entirely if already processed, then immediately marked, so no
    collection is ever traversed, exported, or absorbed twice no matter
    how many paths lead to it.
    """
    current_path = f"{parent_path}/{collection.name}" if parent_path else collection.name

    if collection.name in visited:
        return
    visited.add(collection.name)

    if is_organizational_collection(collection.name):
        results.append(
            pc.CollectionExportResult(
                name=pc.slugify(collection.name),
                collection_path=current_path,
                system=pc.UNCLASSIFIED,
                output=None,
                status="skipped",
                reason="organizational/label collection — skipped by design, not exported",
            )
        )
        for child in collection.children:
            find_export_boundaries(
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
                visited,
            )
        return

    # Scene Collection (the scene's root/master collection) and numbered
    # system roots (its direct children — "1 Skeletal system", "2
    # Muscular system", etc.) are traversal-only by definition: neither
    # may ever become an export boundary itself, no matter what direct
    # mesh objects it happens to hold (a stray root-level mesh, a
    # system-level overview mesh). Treating either as a boundary absorbs
    # every real structure beneath it into one oversized, meaningless
    # export — the confirmed cause of Scene Collection itself being
    # attempted (and failing) as an export, of whole systems like
    # "Cardiovascular system" and "Visceral systems" showing zero-height
    # bounding boxes, and of only ~9 exports appearing (one per system)
    # instead of each individual meaningful anatomical collection
    # (Frontal Bone, Femur, Pelvis, Heart, Lateral Plantar Nerve, ...)
    # nested underneath them. `parent_path == ""` covers every direct
    # child of Scene Collection (i.e. every system root) regardless of
    # naming; the numeric-prefix pattern is a defensive backstop for a
    # numbered collection reached any other way.
    is_scene_root = collection == bpy.context.scene.collection
    is_numbered_system_root = parent_path == "" or bool(re.match(r"^\d+[\s._-]", collection.name))

    if is_scene_root or is_numbered_system_root:
        direct_meshes, restore_state = [], {}
    else:
        direct_meshes, restore_state = gather_direct_objects_with_instances(collection)

    if direct_meshes:
        descendant_meshes, organizational_names, descendant_restore = gather_all_descendant_meshes(
            collection, visited
        )
        restore_state.update(descendant_restore)

        seen_names = {obj.name for obj in direct_meshes}
        all_meshes = list(direct_meshes)
        for obj in descendant_meshes:
            if obj.name not in seen_names:
                seen_names.add(obj.name)
                all_meshes.append(obj)

        for org_name in organizational_names:
            results.append(
                pc.CollectionExportResult(
                    name=pc.slugify(org_name),
                    collection_path=f"{current_path}/{org_name}",
                    system=pc.UNCLASSIFIED,
                    output=None,
                    status="skipped",
                    reason="organizational/label collection — absorbed check only, not exported",
                )
            )

        result = export_boundary(
            collection,
            current_path,
            top_level_name,
            all_meshes,
            keyword_mapping,
            hierarchy_mapping,
            output_dir,
            force,
            dry_run,
            generate_previews,
        )
        results.append(result)
        restore_visibility(restore_state)
        return  # boundary found — do NOT recurse further as separate exports

    # No direct meshes here — pure pass-through grouping node. Restore
    # anything gather_direct_objects_with_instances may have touched
    # (normally nothing, since there were no direct meshes) and recurse.
    restore_visibility(restore_state)
    for child in collection.children:
        find_export_boundaries(
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
            visited,
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
        # The listing pass already decided this collection IS a boundary
        # (it owns direct mesh objects); redo the same absorption here so
        # both modes can never disagree about what gets exported.
        #
        # Boundary decision order (must match find_export_boundaries
        # exactly, so the two modes can never disagree):
        #   1. organizational collection? -> SKIP immediately. Decided
        #      first and wins outright — a "surface of X" collection can
        #      very well own real mesh geometry of its own (it's a
        #      fragment of the parent structure, not empty), so "has
        #      direct mesh objects" must never be consulted before
        #      organizational status has been ruled out.
        #   2. wrapper/pass-through collection (no direct meshes, not
        #      organizational)? -> this mode exports exactly one
        #      already-decided boundary and never traverses, so reaching
        #      this mode at all is an upstream boundary-detection
        #      disagreement; report it as a genuine failure.
        #   3. meaningful anatomical collection (has direct meshes, not
        #      organizational)? -> gather descendant meshes, export once.
        # "has direct mesh objects" is NEVER, by itself, the export
        # boundary test — only step 3 uses it, after 1 has already ruled
        # out organizational collections.
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
        elif is_organizational_collection(collection.name):
            # Step 1 — organizational always wins, regardless of whether
            # this collection happens to own direct mesh objects.
            results.append(
                pc.CollectionExportResult(
                    name=pc.slugify(collection.name),
                    collection_path=only_collection_path,
                    system=pc.UNCLASSIFIED,
                    output=None,
                    status="skipped",
                    reason="organizational/label collection — skipped by design, not exported",
                )
            )
        else:
            top_level_name = find_top_level_ancestor_name(collection) or collection.name
            direct_meshes, restore_state = gather_direct_objects_with_instances(collection)

            if not direct_meshes:
                # Step 2 — wrapper/pass-through reaching single-collection
                # mode: organizational has already been ruled out above,
                # so this is a genuine "not a valid boundary" failure, not
                # a skip.
                restore_visibility(restore_state)
                results.append(
                    pc.CollectionExportResult(
                        name=pc.slugify(collection.name),
                        collection_path=only_collection_path,
                        system=pc.classify_hierarchical(
                            top_level_name, collection.name, hierarchy_mapping, keyword_mapping
                        ),
                        output=None,
                        status="failed",
                        reason=(
                            "collection has no direct mesh objects — not a valid export boundary"
                        ),
                    )
                )
            else:
                # Step 3 — meaningful anatomical collection: gather
                # descendants and export once.
                # Fresh, call-local visited set: this subprocess handles exactly
                # one already-decided boundary, so it only needs to guard
                # against re-absorbing a DAG-linked descendant twice within
                # this single export, not against other boundaries/subprocesses.
                visited: set[str] = set()
                descendant_meshes, _org_names, descendant_restore = gather_all_descendant_meshes(
                    collection, visited
                )
                restore_state.update(descendant_restore)

                seen_names = {obj.name for obj in direct_meshes}
                all_meshes = list(direct_meshes)
                for obj in descendant_meshes:
                    if obj.name not in seen_names:
                        seen_names.add(obj.name)
                        all_meshes.append(obj)

                result = export_boundary(
                    collection,
                    only_collection_path,
                    top_level_name,
                    all_meshes,
                    keyword_mapping,
                    hierarchy_mapping,
                    output_dir,
                    force,
                    dry_run,
                    generate_previews,
                )
                results.append(result)
                restore_visibility(restore_state)
    else:
        # Full-atlas listing/walk mode.
        logger.info("[blender] Loaded %d classification keywords", len(keyword_mapping))
        logger.info("[blender] Loaded %d hierarchy system mappings", len(hierarchy_mapping))
        logger.info("[blender] Traversing Z-Anatomy collections in the active scene…")

        root_collection = bpy.context.scene.collection

        # Single set shared across the ENTIRE walk (both entry points
        # below). Blender's collection hierarchy is a DAG — a collection
        # can be linked under more than one parent — and this is what
        # confirmed-duplicate-traversal through "Scene Collection" and
        # "Bonus collection" requires: without a run-wide visited set, a
        # multiply-linked collection gets discovered again via its second
        # parent path and processed (and exported) a second time.
        visited: set[str] = set()

        for top_level in root_collection.children:
            find_export_boundaries(
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
                visited,
            )

        # The scene's own root collection can (rarely) hold loose mesh
        # objects directly, outside any named sub-collection.
        root_meshes = [obj for obj in root_collection.objects if obj.type == "MESH"]
        if root_meshes:
            find_export_boundaries(
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
                visited,
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