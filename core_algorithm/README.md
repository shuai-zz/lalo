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

Output directories must be absent or empty. Generated artifacts belong under
`core_algorithm/output/`, which is ignored by Git.

## Experiment rule

Each experiment should state the visual or printability hypothesis, retain a
repeatable input, compare its output with the baseline, and record whether it
should be discarded or proposed for the production package. Do not edit both
copies of an algorithm in the same exploratory change.
