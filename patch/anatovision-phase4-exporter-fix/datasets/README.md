# `datasets/`

This folder is reserved for dataset manifests, download scripts, and
licensing notes for the open educational imaging datasets AnatoVision
uses. It does **not** hold raw imaging files — those are large, mostly
DICOM/NIfTI binaries that don't belong in version control (see the root
`.gitignore`).

## Rules

- Only open educational datasets. Never scrape copyrighted material
  improperly.
- Every dataset must have a documented source and license before any code
  references it.
- Radiopaedia content may only be used where its specific licensing
  permits — check per-case, not per-dataset.

## Candidate sources (per the project constitution)

| Source | What it provides | Notes |
| --- | --- | --- |
| [TCIA](https://www.cancerimagingarchive.net/) | CT, MRI, PET collections | Per-collection license (often CC BY / CC BY-NC) |
| [NIH Chest X-ray](https://nihcc.app.box.com/v/ChestXray-NIHCC) | Chest X-ray images | Public domain-style NIH license |
| [Open Anatomy](https://www.openanatomy.org/) | Labeled anatomical atlases | Mixed open licenses, check per atlas |
| [Visible Human Project](https://www.nlm.nih.gov/research/visible/visible_human.html) | Full-body cryosection / CT / MRI | NLM license agreement required |
| [MedPix](https://medpix.nlm.nih.gov/) | Case-based teaching images | U.S. Government work / open use |
| [Radiopaedia](https://radiopaedia.org/) | Case images, articles | Per-case license — verify before use |

## What belongs here (future phases)

- `manifests/` — JSON/YAML lists of which cases/series are used, with
  source + license recorded per entry
- `scripts/` — download and preprocessing scripts (kept separate from the
  root-level `scripts/` dev tooling)
- Nothing containing patient-identifiable data, ever — only de-identified
  public datasets.

Nothing in this folder is built yet; it exists so Phase 2+ has a clear,
pre-approved place to put dataset work without restructuring the repo.
