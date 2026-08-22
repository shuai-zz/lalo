# Lalo

> Turn anyone into a printable block figure.

Lalo is an open-source tool that turns a short text prompt and an optional reference photo into a set of 3D-printable, Minecraft-style humanoid parts.

Describe a character such as Spider-Man, Iron Man, or upload a photo of yourself. Lalo extracts the recognizable details—hair, glasses, clothing, colors, masks, and patterns—then builds them as printable voxel geometry and surface relief.

The M2 implementation can now turn a text prompt and optional in-memory image
into a locally validated `CharacterPlan`, then generate printable relief
geometry and a four-color preview. The planner is replaceable; the first
adapter uses OpenAI's Responses API, and Spider-Man and Iron Man remain
available as deterministic offline geometry fixtures.

```bash
python -m pip install -e .
python - <<'PY'
import os

from lalo import (
    OpenAIHTTPTransport,
    OpenAIPlanner,
    PlanRequest,
    generate_m2_artifacts,
)

planner = OpenAIPlanner(
    model=os.environ["LALO_OPENAI_MODEL"],
    transport=OpenAIHTTPTransport(os.environ["OPENAI_API_KEY"]),
)
generate_m2_artifacts(
    PlanRequest("生成一个蜘蛛侠风格的方块小人", seed=42),
    planner,
    "result",
)
PY
```

The command produces:

```text
result/
  stl/                    # 14 separate binary STL parts
  character_plan.json     # cleaned and protected relief plan
  provider_character_plan.json # original locally validated provider plan
  material_grid.json.gz   # retained four-color surface assignments
  manifest.json           # actual bounds, transforms, and file hashes
  planning_metadata.json  # redacted provider and reproducibility metadata
  preview.glb             # detailed, assembled, colored preview
  validation_report.json  # cleanup and topology results
```

For an image request, pass in-memory JPEG, PNG, or WebP bytes:

```python
from pathlib import Path

import os

from lalo import (
    ImageInput,
    OpenAIHTTPTransport,
    OpenAIPlanner,
    PlanRequest,
    generate_m2_artifacts,
)

# Set zero_retention=True only after confirming ZDR for this OpenAI project.
image_planner = OpenAIPlanner(
    model=os.environ["LALO_OPENAI_MODEL"],
    transport=OpenAIHTTPTransport(os.environ["OPENAI_API_KEY"]),
    zero_retention=True,
)

request = PlanRequest(
    "保留黑框眼镜，但把照片里的衣服改成红色夹克",
    image=ImageInput(Path("person.jpg").read_bytes(), "image/jpeg"),
    seed=42,
)
generate_m2_artifacts(request, image_planner, "result")
```

Image generation requires `OpenAIPlanner(..., zero_retention=True)`, but that
flag is only a declaration checked by Lalo. It does not enable Zero Data
Retention at OpenAI. Set it only after the deployer has independently confirmed
that the configured organization and endpoint have the required retention
controls. Every adapter request sets `store: false` regardless.

For fully offline geometry testing, use `generate_m1_artifacts()` with
`spider_man_plan()` or `iron_man_plan()`. The M0 untextured generator remains
available as `generate_m0_artifacts()`.

## What Lalo will generate

- 14 separate STL body parts for an articulated humanoid figure
- Minecraft-like proportions at a default assembled height of 80 mm
- Pixelated raised and engraved surface details
- A colored GLB assembly preview
- A manifest containing assembly transforms and material information
- Geometry validated for entry-level FDM printing with a 0.4 mm nozzle

The first release generates body parts without joint sockets. A reusable joint library and robust boolean insertion will be added separately. STL is the initial print format; multicolor 3MF/AMS export is planned.

## How it works

```text
text + optional image
        ↓
multimodal model → constrained CharacterPlan
        ↓
printability cleanup and protected-surface checks
        ↓
deterministic voxel geometry compiler
        ↓
validated STL parts + colored GLB preview
```

The AI model describes bounded surface maps and character features—it does not generate arbitrary mesh code. A deterministic local geometry engine turns that plan into axis-aligned voxel meshes. This keeps the output reproducible, inspectable, and printable.

Lalo is designed to support interchangeable multimodal providers. Geometry processing runs locally on CPU and does not require Blender.

## MVP scope

The MVP focuses on:

- Chinese and English prompts
- One optional image containing exactly one person or character
- Standard bipedal humanoids
- Short or medium block hair, glasses, masks, facial hair, clothing details, and mild armor
- macOS and Linux
- CLI-first, self-hosted usage

Non-humanoids, capes, weapons, long hanging hair, user editing, joints, 3MF, Windows, Docker, and a web interface are outside the first milestone.

## Project status

M0 and M1 are complete. The M2 software path is implemented: provider protocol,
strict JSON codec, bounded correction, single-subject rejection, OpenAI
multimodal adapter, privacy helpers, reproducibility metadata, and end-to-end
M1 artifact generation are covered by offline tests on macOS and Linux.

M2 acceptance is not yet complete. It still requires four appropriately
licensed personal photos, execution of all ten golden cases against a configured
live provider, human recognizability scoring, and review of the resulting
artifacts without manual mesh edits. Those assets are deliberately not stored
in this repository yet. The remaining roadmap is:

1. Complete the ten-case M2 acceptance run
2. Build the CLI/ZIP workflow and perform owner physical print validation
3. Add joint insertion and multicolor 3MF support

See [SPEC.md](./SPEC.md) for the complete product and technical specification.

## Privacy

Lalo is intended for open-source, self-hosted use. The core planner accepts
images in memory and never includes prompt text, image bytes, Base64 content,
credentials, or raw provider responses in its planning metadata. A helper for
adapters that require a temporary image file removes its private copy on normal
and exceptional exits; it never deletes the user's original photo. When an
external AI provider is configured, that provider's data-retention policy still
applies.

## Contributing

The project is at an early stage. Design discussions, printable test cases, geometry experiments, and provider adapters are welcome.

## License

The license has not been selected yet.
