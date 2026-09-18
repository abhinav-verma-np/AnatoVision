# `scripts/`

Cross-cutting developer scripts that don't belong to just the frontend or
just the backend.

- **`setup.sh`** — one-shot local dev bootstrap (backend venv + deps,
  frontend `npm install`, copies `.env.example` files). Run via
  `./scripts/setup.sh` or `make setup`.

## Z-Anatomy asset pipeline

Converts a manually-downloaded Z-Anatomy dataset into optimized `.glb`
models sorted into `frontend/public/models/<system>/`, with an
auto-generated `manifest.json`. Never downloads anything itself.

| File | Role |
| --- | --- |
| `process_models.py` | Main entrypoint — scan, classify, convert, compress, manifest, in one run |
| `model_convert.py` | Format dispatch: `.blend` → Blender CLI, everything else → trimesh |
| `export_blender.py` | Runs *inside* Blender (`--python`) to export the loaded scene to `.glb` |
| `compression.py` | Draco/Meshopt hooks via the optional `gltf-transform` CLI |
| `generate_manifest.py` | Rebuilds `frontend/public/models/manifest.json` from whatever `.glb` files exist on disk — standalone-runnable |
| `pipeline_common.py` | Shared constants/helpers (body systems, slugify, classify, logging) used by the scripts above |

Setup:

```bash
pip install -r scripts/requirements.txt --break-system-packages
```

Usage:

```bash
# 1. Download Z-Anatomy yourself, extract into assets/raw/Z-Anatomy/
# 2. Run the pipeline
python scripts/process_models.py

# Options
python scripts/process_models.py --dry-run          # scan + classify only
python scripts/process_models.py --force             # reprocess existing outputs
python scripts/process_models.py --compress draco     # requires gltf-transform CLI
python scripts/process_models.py --blender-exe /path/to/blender
```

Output: classified `.glb` files under `frontend/public/models/<system>/`
(unrecognized names go to `.../unclassified/` without failing the run),
a regenerated `frontend/public/models/manifest.json`, and a full log at
`logs/model_processing.log`.

Day-to-day commands (dev servers, lint, test, Docker) are exposed through
the root `Makefile` — see the main README's "Development workflow"
section. This folder is for setup/bootstrap automation, and is a
reserved location for future cross-cutting scripts (e.g. dataset
provisioning helpers) rather than a place for one-off ad hoc scripts.
