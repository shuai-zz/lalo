# Lalo

> Turn anyone into a printable block figure.

Lalo turns a Chinese or English description—and optionally one reference
photo—into Minecraft-style humanoid body parts for FDM printing. It uses a
multimodal model to create an inspectable four-view design sheet, then compiles
that sheet locally into voxel shape, color regions, raised details, and engraved
grooves. Blender is not required.

The current release produces 14 separate STL files, a colored GLB preview, the
retained material grid, validation metadata, and a deterministic ZIP. Joint
geometry and 3MF are intentionally not included yet.

## Install

Lalo requires Python 3.11 or newer and currently targets macOS and Linux.

```bash
git clone https://github.com/shuai-zz/lalo.git
cd lalo
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Check the available provider and local configuration without making a network
request:

```bash
lalo providers
lalo config check
```

## Configure the design provider

The included provider uses OpenAI's Responses and image-generation APIs:

```bash
export OPENAI_API_KEY="..."
export LALO_OPENAI_VISION_MODEL="gpt-5.4"       # optional default
export LALO_OPENAI_IMAGE_MODEL="gpt-image-2"   # optional default
```

`OPENAI_BASE_URL` may point to an OpenAI-compatible service, but the service
must implement both the structured Responses request and image-generation
request used by Lalo. A chat/vision-only endpoint is not sufficient for the
complete design stage.

`LALO_OPENAI_ZERO_RETENTION=1` is required for photo input. This is a local
declaration, not a provider setting: enable it only after confirming that the
configured provider account and endpoint actually meet your retention needs.
Lalo also sends `store: false`.

## Generate a figure

Generation is deliberately split into two inspectable stages.

First create the design package:

```bash
lalo design \
  --prompt "一个红蓝配色、胸前有蜘蛛标志的方块英雄" \
  --seed 42 \
  --output ./design
```

For a personal figure, add a single-person JPEG, PNG, or WebP photo:

```bash
LALO_OPENAI_ZERO_RETENTION=1 lalo design \
  --prompt "保留黑框眼镜和蓝色夹克，做成方块小人" \
  --image ./person.jpg \
  --seed 42 \
  --output ./design
```

Inspect `design/sheet.png` and the four orthographic views, then compile them
locally. The default assembled height is 96 mm:

```bash
lalo compile-design ./design --height 96 --output ./result
lalo validate ./result
```

Each output path must not already exist. This prevents accidental overwrite of
designs or printable files.

## Outputs

The design stage writes no source photo:

```text
design/
  identity.json          # bounded identity features
  sheet.png              # four-view source sheet
  front.png
  right.png
  back.png
  left.png
  design-metadata.json   # redacted reproducibility metadata
```

The offline compiler writes:

```text
result/
  stl/                    # 14 part-local binary STL files
  character_plan.json     # final protected material/relief plan
  material_grid.json.gz   # retained four-color surface assignments
  manifest.json           # dimensions, assembly transforms, sizes, hashes
  preview.glb             # assembled colored preview
  validation_report.json  # topology and printability results
  result.zip              # deterministic archive of all files above
```

`lalo validate` independently checks the plan, compressed material grid, GLB
header, all 14 manifest entries and STL hashes, topology report, safe relative
paths, and exact ZIP contents. It returns a nonzero status with stable error
codes if anything is missing or modified.

## Geometry pipeline

```text
text + optional photo
        ↓ external provider
identity spec + orthographic design sheet
        ↓ local CPU pipeline
part crops → four-color sampling → relief inference
        ↓
voxel head visual hull + protected raised/engraved surface geometry
        ↓
14 watertight STL parts + GLB + manifest + ZIP
```

The model creates design images and constrained identity data; it does not write
mesh code. Deterministic local code samples the design and generates the actual
geometry. The head uses a multi-view voxel visual hull, so its profile, back of
the head, and identified features such as glasses can have physical depth rather
than being only a flat texture. Other body parts currently keep canonical block
envelopes with voxel relief.

## Scope and limitations

The current scope is one standard bipedal humanoid, one optional subject, at
most four sampled colors, and basic 0.4 mm-nozzle/0.2 mm-layer FDM constraints.
It supports short or medium block hair, glasses, masks, facial hair, clothing
details, and mild armor.

Not yet included:

- joint pegs, sockets, tolerance fitting, or boolean joint insertion;
- 3MF/AMS export (STL is geometry-only; GLB is the color preview);
- user editing, a web UI, Windows, Docker, non-humanoids, weapons, capes, or
  long hanging hair;
- guaranteed likeness or famous-character recognition from every generated
  design sheet.

Automated geometry and package validation passes on macOS and Linux. Physical
printing remains an owner-run acceptance step: Spider-Man, Iron Man, and one
photo-based figure still need to be sliced and printed with the target FDM
profile before the MVP can claim physical validation.

## Privacy

Lalo reads a source photo into memory and does not copy it into either output
package. Prompt text, image bytes, Base64 payloads, credentials, and raw provider
responses are excluded from saved metadata. External-provider retention and
logging policies still apply, so self-hosters must assess their configured
provider separately.

## Development

Run the offline test suite with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

All feature changes are delivered through a focused GitHub issue and pull
request. See [AGENTS.md](./AGENTS.md) for repository workflow rules and
[SPEC.md](./SPEC.md) for the product and technical specification.

The project does not have a selected license yet.
