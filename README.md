# Lalo

> Turn anyone into a printable block figure.

Lalo is an open-source tool that turns a short text prompt and an optional reference photo into a set of 3D-printable, Minecraft-style humanoid parts.

Describe a character such as Spider-Man, Iron Man, or upload a photo of yourself. Lalo extracts the recognizable details—hair, glasses, clothing, colors, masks, and patterns—then builds them as printable voxel geometry and surface relief.

```bash
lalo generate \
  --prompt "保留黑框眼镜和蓝色夹克" \
  --image person.jpg \
  --height 80 \
  --seed 42 \
  --output ./result
```

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

Lalo is currently in the specification and geometry-prototyping stage. The implementation roadmap is:

1. Deterministic voxel geometry compiler and STL validation
2. Surface relief and material-map compiler
3. Pluggable multimodal character planner
4. End-to-end CLI and physical print validation
5. Joint insertion and multicolor 3MF support

See [SPEC.md](./SPEC.md) for the complete product and technical specification.

## Privacy

Lalo is intended for open-source, self-hosted use. Reference images should be kept only for the duration of generation and must not be written to logs. When an external AI provider is configured, its data-retention policy still applies.

## Contributing

The project is at an early stage. Design discussions, printable test cases, geometry experiments, and provider adapters are welcome.

## License

The license has not been selected yet.
