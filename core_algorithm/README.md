# Lalo core algorithm experiment

This directory is an isolated snapshot of Lalo's deterministic geometry
kernel. It exists so geometry quality can be evaluated and changed without
coupling experiments to the production package, provider integration, or CLI.

## Boundary

Included:

- canonical 14-part body proportions;
- voxel occupancy and exposed-face meshing;
- per-face material, raised, engraved, and silhouette detail maps;
- protected mating surfaces and FDM detail cleanup;
- mesh validation, binary STL export, and canonical manifest generation.

Excluded:

- AI designers and planners;
- image generation, design-sheet parsing, and provider configuration;
- the production CLI, GLB/ZIP packaging, and HTTP service concerns.

The package is intentionally named `lalo_core`, so experiments cannot silently
import or modify the production `lalo` package. This is a snapshot rather than
a shared source directory: changes made here do not affect `src/lalo`, and any
successful algorithm must be deliberately reviewed before being ported back.

## Run independently

From this directory:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

Generate the baseline 14-part STL set without using the production package:

```bash
PYTHONPATH=src python -c 'from lalo_core import write_canonical_stls; write_canonical_stls("output/baseline")'
```

Convert a strict front/back or front/right/back/left Minecraft character sheet
into an editable standard 64x64 skin and a six-panel review sheet:

```bash
PYTHONPATH=src python -m lalo_core.skin_sampling \
  ./front-back-source.png \
  --output ./output/image-first
```

The preferred source contains exactly four separated, orthographic, full-body
figures ordered front, right, back, left. A legacy two-panel front/back sheet is
also accepted. Every figure must use the same scale, the classic 8/12/12
head/body/leg height proportions, complete rectangular body silhouettes, a
uniform background, and texture-only hair and clothing details.

Four-panel input observes front, back, left, and right colors directly. For
legacy two-panel input, side faces remain deterministic blends of the nearest
observed edges. Top and bottom faces are approximations in both modes until an
additional reference or a learned completion stage is added.

Render the sampled skin on the fixed classic block body for interactive review:

```bash
PYTHONPATH=src python -m lalo_core.skin_glb \
  ./output/image-first/skin.png \
  --output ./output/image-first/preview.glb
```

The GLB contains six named cuboids, one embedded PNG texture, nearest-neighbor
sampling, and the standard 32-unit assembled height. It intentionally excludes
the optional outer skin layer, slim arms, animation, joints, and print relief.

Output directories must be absent or empty. Generated artifacts belong under
`core_algorithm/output/`, which is ignored by Git.

## Experiment rule

Each experiment should state the visual or printability hypothesis, retain a
repeatable input, compare its output with the baseline, and record whether it
should be discarded or proposed for the production package. Do not edit both
copies of an algorithm in the same exploratory change.
