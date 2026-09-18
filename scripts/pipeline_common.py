"""
Shared constants and helpers for the AnatoVision Z-Anatomy asset pipeline.

Imported by process_models.py and generate_manifest.py so both scripts
agree on folder names, supported formats, slugification, and logging
setup without duplicating any of it.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Must match frontend/lib/data/anatomy/*.ts system ids exactly — these are
# both the frontend/public/models/ subfolder names and the manifest's
# "system" values. Extended with the additional Z-Anatomy top-level
# groupings (joints, lymphoid, visceral, regions) alongside the original
# educational-content systems.
BODY_SYSTEMS: tuple[str, ...] = (
    "skeletal",
    "muscular",
    "nervous",
    "cardiovascular",
    "respiratory",
    "digestive",
    "urinary",
    "reproductive",
    "joints",
    "lymphoid",
    "visceral",
    "regions",
)

UNCLASSIFIED = "unclassified"
ALL_SYSTEM_FOLDERS: tuple[str, ...] = (*BODY_SYSTEMS, UNCLASSIFIED)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".blend", ".obj", ".fbx", ".stl", ".gltf", ".glb"}
)

# Repo-root-relative defaults. scripts/ lives one level below repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW_DIR = REPO_ROOT / "assets" / "raw" / "Z-Anatomy"
DEFAULT_PROCESSED_DIR = REPO_ROOT / "assets" / "processed"
DEFAULT_MODELS_DIR = REPO_ROOT / "frontend" / "public" / "models"
DEFAULT_MANIFEST_PATH = DEFAULT_MODELS_DIR / "manifest.json"
DEFAULT_MAPPING_PATH = REPO_ROOT / "config" / "model_mapping.json"
DEFAULT_HIERARCHY_MAPPING_PATH = REPO_ROOT / "config" / "system_hierarchy_mapping.json"
DEFAULT_LOG_PATH = REPO_ROOT / "logs" / "model_processing.log"
DEFAULT_EXPORT_SCRIPT = Path(__file__).resolve().parent / "export_blender.py"

ProcessStatus = Literal["processed", "skipped", "failed"]


@dataclass
class ProcessResult:
    """Outcome of converting a single source model file."""

    name: str
    source: Path
    system: str
    output: Path | None
    status: ProcessStatus
    reason: str = ""
    elapsed_seconds: float = 0.0


_SLUG_INVALID_CHARS = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Turn a source filename stem into a safe, URL-friendly asset name.

    Preserves the recognizable identity of the original name (case and
    separators aside) — "Left Femur" -> "left-femur", "Heart_v2" -> "heart-v2".
    """
    slug = name.strip().lower()
    slug = _SLUG_INVALID_CHARS.sub("-", slug)
    slug = slug.strip("-")
    return slug or "model"


def load_model_mapping(mapping_path: Path) -> dict[str, str]:
    """Load config/model_mapping.json. Missing file -> empty mapping
    (everything falls through to "unclassified" rather than crashing)."""
    if not mapping_path.exists():
        return {}
    with mapping_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"{mapping_path} must contain a JSON object of keyword -> system")
    return {str(k).lower(): str(v) for k, v in raw.items()}


def classify_model(original_name: str, mapping: dict[str, str]) -> str:
    """Classify a model into a body system using the keyword mapping.

    Matches keywords as case-insensitive substrings of the *original*
    filename stem (before slugification, so multi-word keywords like
    "spinal cord" still match "Spinal Cord Cervical.obj"). Longer keywords
    are checked first so specific terms win over generic ones.

    This is the FALLBACK tier only (see classify_hierarchical below) —
    call it with a LEAF structure name, never a full hierarchical path.
    Matching against a concatenated ancestor path is exactly what caused
    structures like "Lateral Plantar Nerve" to be misclassified as
    skeletal (an ancestor collection's name containing a skeletal keyword
    contaminated an unrelated descendant's classification).
    """
    haystack = original_name.lower()
    for keyword in sorted(mapping, key=len, reverse=True):
        if keyword in haystack:
            system = mapping[keyword]
            if system in BODY_SYSTEMS:
                return system
    return UNCLASSIFIED


def load_system_hierarchy_mapping(path: Path) -> dict[str, tuple[str, ...]]:
    """Load config/system_hierarchy_mapping.json: system slug -> normalized
    candidate top-level Z-Anatomy collection names. Missing file -> empty
    mapping (classify_hierarchical then falls straight through to the
    keyword fallback for everything)."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object of system -> [candidate names]")
    return {str(k): tuple(str(v).lower() for v in values) for k, values in raw.items()}


_SYSTEM_NAME_NOISE = re.compile(r"[^a-z0-9 ]+")


def _normalize_system_name(name: str) -> str:
    return _SYSTEM_NAME_NOISE.sub("", name.lower()).strip()


def classify_by_top_level_name(
    top_level_name: str, hierarchy_mapping: dict[str, tuple[str, ...]]
) -> str:
    """Classify using ONLY the curated top-level-collection-name table —
    never a substring scan of a leaf name or a concatenated path. This is
    tier 1 (highest priority): it trusts Z-Anatomy's own authored
    hierarchy instead of re-deriving system membership from text."""
    normalized = _normalize_system_name(top_level_name)
    for system, candidates in hierarchy_mapping.items():
        if normalized in candidates and system in BODY_SYSTEMS:
            return system
    return UNCLASSIFIED


def classify_hierarchical(
    top_level_name: str,
    leaf_name: str,
    hierarchy_mapping: dict[str, tuple[str, ...]],
    keyword_mapping: dict[str, str],
) -> str:
    """Three-tier classification, in priority order:

    1. Hierarchy: does the structure's TOP-LEVEL ancestor collection name
       match a known system in config/system_hierarchy_mapping.json?
    2. (explicit mapping is tier 1 itself — config/system_hierarchy_mapping.json
       IS the explicit mapping; there is no separate tier here by design,
       since maintaining two "explicit" tables would just reintroduce the
       ambiguity this fix removes)
    3. Keyword fallback: classify_model() against the LEAF name only
       (never the full path), for structures whose top-level ancestor
       isn't in the curated table yet.
    """
    hierarchy_result = classify_by_top_level_name(top_level_name, hierarchy_mapping)
    if hierarchy_result != UNCLASSIFIED:
        return hierarchy_result
    return classify_model(leaf_name, keyword_mapping)


def ensure_output_dirs(models_dir: Path) -> None:
    for folder in ALL_SYSTEM_FOLDERS:
        (models_dir / folder).mkdir(parents=True, exist_ok=True)


def setup_logger(log_path: Path, name: str = "anatovision.pipeline") -> logging.Logger:
    """Console + file logger. File gets full detail; console stays terse."""
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes)}m {secs:.0f}s"


# ===========================================================================
# Z-Anatomy Native Exporter additions
# ---------------------------------------------------------------------------
# Everything below supports export_z_anatomy.py / blender_export_collections.py.
# The original per-file pipeline (process_models.py, model_convert.py,
# compression.py) is untouched and keeps working against everything above.
# ===========================================================================

DEFAULT_COLLECTION_EXPORT_SCRIPT = Path(__file__).resolve().parent / "blender_export_collections.py"
DEFAULT_TEMPLATE_NAME = "Z-Anatomy"


@dataclass
class CollectionExportResult:
    """Outcome of exporting a single Blender collection to .glb."""

    name: str
    collection_path: str
    system: str
    output: Path | None
    status: ProcessStatus
    reason: str = ""
    elapsed_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)
    preview: Path | None = None

    @staticmethod
    def from_dict(data: dict) -> CollectionExportResult:
        return CollectionExportResult(
            name=data["name"],
            collection_path=data["collection_path"],
            system=data["system"],
            output=Path(data["output"]) if data.get("output") else None,
            status=data["status"],
            reason=data.get("reason", ""),
            elapsed_seconds=float(data.get("elapsed_seconds", 0.0)),
            warnings=list(data.get("warnings", [])),
            preview=Path(data["preview"]) if data.get("preview") else None,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "collection_path": self.collection_path,
            "system": self.system,
            "output": str(self.output) if self.output else None,
            "status": self.status,
            "reason": self.reason,
            "warnings": self.warnings,
            "preview": str(self.preview) if self.preview else None,
            "elapsed_seconds": self.elapsed_seconds,
        }


def find_blender_executable(blender_exe: str = "blender") -> str | None:
    """Resolve a usable Blender executable, or None if it can't be found.

    Checks PATH first (handles 'blender' / 'blender.exe' cross-platform via
    shutil.which), then falls back to treating blender_exe as a literal path.
    """
    resolved = shutil.which(blender_exe)
    if resolved:
        return resolved
    candidate = Path(blender_exe)
    if candidate.is_file():
        return str(candidate)
    return None


def _blender_config_roots() -> list[Path]:
    """Platform-specific roots under which Blender keeps one folder per
    installed version (e.g. '4.2/'). Only returns roots that exist."""
    system = platform.system()
    home = Path.home()
    roots: list[Path] = []

    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            roots.append(Path(appdata) / "Blender Foundation" / "Blender")
    elif system == "Darwin":
        roots.append(home / "Library" / "Application Support" / "Blender")
    else:  # Linux and other POSIX systems
        roots.append(home / ".config" / "blender")

    return [r for r in roots if r.exists()]


def find_z_anatomy_template(template_name: str = DEFAULT_TEMPLATE_NAME) -> Path | None:
    """Locate the installed Z-Anatomy Blender Application Template.

    Application Templates live at:
        <blender-config-root>/<version>/scripts/startup/bl_app_templates_user/<name>/
    across every installed Blender version folder. Returns the template
    directory if found, or None if Z-Anatomy.zip hasn't been installed —
    this repository never installs it automatically (permanent project
    rule: upstream Z-Anatomy files are read-only and developer-managed).
    """
    for root in _blender_config_roots():
        for version_dir in sorted(root.glob("*"), reverse=True):
            candidate = (
                version_dir / "scripts" / "startup" / "bl_app_templates_user" / template_name
            )
            if candidate.is_dir():
                return candidate
    return None


def suggest_template_install_path(template_name: str = DEFAULT_TEMPLATE_NAME) -> str:
    """Best-effort human-readable install path to show in error messages
    when the template isn't found (there may be no existing version folder
    to detect yet, e.g. on a fresh Blender install)."""
    system = platform.system()
    if system == "Windows":
        base = r"%APPDATA%\Blender Foundation\Blender\<version>"
    elif system == "Darwin":
        base = "~/Library/Application Support/Blender/<version>"
    else:
        base = "~/.config/blender/<version>"
    return f"{base}/scripts/startup/bl_app_templates_user/{template_name}/"


# ---------------------------------------------------------------------------
# Checkpointing (per-collection resume support)
# ---------------------------------------------------------------------------

DEFAULT_CHECKPOINT_PATH = REPO_ROOT / "logs" / "export_checkpoint.json"


def load_checkpoint(checkpoint_path: Path) -> dict[str, dict]:
    """Load the per-collection checkpoint file. Missing/corrupt file ->
    empty checkpoint (never fatal — worst case, everything just re-runs)."""
    if not checkpoint_path.exists():
        return {}
    try:
        with checkpoint_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_checkpoint(checkpoint: dict[str, dict], checkpoint_path: Path) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = checkpoint_path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2, sort_keys=True)
    tmp_path.replace(checkpoint_path)  # atomic-ish swap so a crash mid-write can't corrupt it
