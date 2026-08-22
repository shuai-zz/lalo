# Lalo MVP Product and Technical Specification

Status: Final draft  
Date: 2026-08-22

## 1. Product definition

Lalo is an open-source, self-hostable tool that turns a one-line Chinese or English character description, plus an optional single reference image, into a set of printable, Minecraft-proportioned humanoid STL parts.

The MVP is for 3D-printing hobbyists using basic FDM printers. It optimizes for recognizable characters and reliable printing rather than photorealistic likeness or unrestricted body shapes.

### 1.1 Primary use cases

1. Text only: `生成一个蜘蛛侠风格的可动方块小人`.
2. Text plus image: upload one personal photo and request a block figure that preserves recognizable cues such as hairstyle, glasses, facial hair, clothing, and dominant colors.
3. Download separate, validated STL body parts. The user will later combine them with a separately designed joint library.

### 1.2 Product principles

- Character recognizability is more important than exact visual reproduction.
- Geometry generation is deterministic and programmatic. An AI model describes the character; it does not write arbitrary mesh code.
- Printability constraints override tiny visual details.
- Photos are transient inputs and are deleted as soon as the generation job no longer needs them.
- The AI provider is replaceable and selected/configured by the deployer.
- Famous characters are allowed during prototyping. The deployer is responsible for copyright and trademark compliance.

## 2. MVP scope

### 2.1 Included

- One required text prompt, in Chinese or English.
- One optional reference image containing exactly one person or character.
- Human-shaped, bipedal characters only.
- A single Minecraft-like body proportion.
- Default assembled height of 80 mm, overridable with `height_mm`.
- Block-shaped hands and feet, with no fingers.
- Recognizable surface relief and limited silhouette additions.
- Separate STL files for all body parts.
- A GLB assembled preview, PNG preview, intermediate character description, and manifest.
- Seeded reproducibility, subject to the selected model/provider and model-version pinning.
- macOS and Linux CLI support.
- Automated geometry and printability validation.

### 2.2 Supported appearance features

- Short and medium block-shaped hair.
- Glasses, masks, eye patches, facial hair, and simplified facial features.
- Collars, ties, belts, pockets, suit lines, web lines, and armor panel lines.
- Mild shoulder armor.
- Shoe upper and sole relief.
- Small fused silhouette features such as ears and compact hair masses.

All additions are fused into the owning body part and exported as one watertight shell.

### 2.3 Explicit non-goals

- Non-humanoids, quadrupeds, wings, tails, extra limbs, or extra heads.
- Long hanging hair, skirts, capes, wide hat brims, backpacks, weapons, or handheld props.
- User editing, conversational revision, rigging, animation, or web UI.
- Joint design, joint fitting, assembly instructions, or joint boolean insertion in the MVP.
- 3MF and actual multicolor-print export in the MVP.
- Windows and Docker support in the MVP.
- Guaranteed freestanding balance.
- Exact facial likeness from a photo.
- Support-free printing.

## 3. Inputs and precedence

### 3.1 Required input

- `prompt`: non-empty UTF-8 text in Chinese or English.

### 3.2 Optional inputs

- `image`: one JPEG, PNG, or WebP image.
- `height_mm`: assembled height, default `80.0`.
- `seed`: integer, generated and returned when omitted.
- `provider` and `model`: deployment-defined defaults, optionally selectable by the user.

### 3.3 Image rules

- The image must contain exactly one person or character.
- Zero or multiple detected subjects cause a validation error; the system must not silently choose one.
- Front or three-quarter portraits are accepted.
- Missing sides and back may be inferred by the AI.
- For personal photos, recognition is based on hairstyle, glasses, facial hair, clothing, and color blocking—not precise facial geometry.

### 3.4 Conflict resolution

Text overrides the image. The image supplies identity and appearance cues unless the prompt explicitly changes them. Example: a red jacket in the image becomes blue if the text requests a blue jacket.

## 4. Body and part specification

### 4.1 Canonical proportions

The canonical body uses Minecraft-like dimensions measured in master voxels:

| Part | Width | Height | Depth |
|---|---:|---:|---:|
| Head | 8 | 8 | 8 |
| Torso | 8 | 12 | 4 |
| Each complete arm | 4 | 12 | 4 |
| Each complete leg | 4 | 12 | 4 |

Total standing height is 32 master voxels. At the default 80 mm height, one master voxel is 2.5 mm.

The exact split points between upper/lower limb segments and hands/feet are configuration data and may later change to accommodate the joint library. The assembled outer proportions remain canonical unless a future spec version changes them.

### 4.2 Output parts

The MVP exports 14 parts:

1. `head`
2. `torso`
3. `left_upper_arm`
4. `right_upper_arm`
5. `left_forearm`
6. `right_forearm`
7. `left_hand`
8. `right_hand`
9. `left_thigh`
10. `right_thigh`
11. `left_shin`
12. `right_shin`
13. `left_foot`
14. `right_foot`

There is no separate neck or pelvis part. Left and right parts are always exported separately, even when geometrically identical.

### 4.3 Protected joint surfaces

The following surfaces are protected and must remain planar and free of relief or silhouette additions:

- Head bottom.
- Torso top, shoulder interfaces, and hip interfaces.
- Both ends of every upper/lower limb segment.
- Hand-to-forearm, foot-to-shin, and corresponding mating surfaces.

The exact protected masks and clearance volumes will be supplied by the future joint library. Until then, the generator uses configurable rectangular keep-out masks and exports parts without joint cavities or pegs.

## 5. Voxel and relief geometry

### 5.1 Two-resolution representation

- Master grid: 2.5 mm at 80 mm total height; defines body proportions and large silhouette features.
- Detail grid: nominal 0.5 mm at 80 mm total height; defines surface pixels and relief.
- All dimensions scale linearly with `height_mm`, but printability limits are expressed in physical millimeters and do not scale below safe values.

The detail grid is aligned to the master grid. Five detail cells span one master voxel at the default height.

### 5.2 Surface coverage

Relief may cover:

- All six head faces except protected connection areas.
- Torso front, back, left, and right faces.
- The four long side faces of limb pieces.
- Exposed hand and foot faces that do not mate with another part.

Joint/mating faces and normally hidden contact faces are excluded.

### 5.3 Relief operations

The intermediate representation supports:

- `raise`: add outward detail cells.
- `engrave`: remove inward detail cells.
- `silhouette_add`: add a compact feature to the base outline.

The geometry planner chooses raised or engraved treatment per feature. Operations are quantized to the detail grid and clipped against protected masks.

Default printable limits for a 0.4 mm nozzle and 0.2 mm layer height:

- Minimum relief line width: 0.8 mm, rounded up to the detail grid.
- Minimum raised/engraved depth: 0.4 mm.
- Preferred relief depth: 0.5–1.0 mm.
- Minimum residual wall thickness after engraving: 1.2 mm.
- Unsupported isolated detail cells are removed or merged.
- Features below limits are simplified, thickened, merged, or omitted.

### 5.4 Meshing decision

The MVP must use exposed-face extraction from a binary occupancy grid:

1. Build a solid occupancy grid for each body part.
2. Apply validated add/remove operations on the grid.
3. Emit a quad only where an occupied cell touches an empty cell.
4. Greedily merge coplanar adjacent quads where this does not erase material/color boundaries.
5. Triangulate deterministically and weld coincident vertices.

Marching cubes is not used because it produces an interpolated isosurface and undermines the intended axis-aligned block aesthetic. OpenVDB is not a required MVP dependency. The design can later adopt sparse storage if model resolution grows.

## 6. Color model and future 3MF support

STL output is single-color geometry. Nevertheless, the internal representation must preserve a palette and per-surface-cell material assignment.

- Maximum palette size: four colors.
- Colors use sRGB hex values plus semantic names when available.
- The GLB preview displays these colors.
- Relief boundaries may improve paintability but must not create separate color-piece STL files in the MVP.
- The intermediate color grid must be retained in the ZIP so a later 3MF exporter can map cells/faces to AMS materials without rerunning AI inference.

## 7. AI intermediate representation

### 7.1 Provider responsibility

The multimodal provider converts the prompt and optional image into a schema-valid `CharacterPlan`. It must not output STL, mesh code, arbitrary Python, or unrestricted CSG instructions.

The provider receives:

- Prompt and optional image.
- Canonical body layout and permitted feature vocabulary.
- Surface dimensions and protected masks.
- Four-color limit.
- Printability limits.
- Seed and schema version.

### 7.2 CharacterPlan requirements

At minimum, `CharacterPlan` contains:

```json
{
  "schema_version": "1.0",
  "seed": 42,
  "character_summary": "person with black rectangular glasses and blue jacket",
  "palette": [
    {"id": 0, "name": "skin", "srgb": "#C98F65"},
    {"id": 1, "name": "hair", "srgb": "#211A17"},
    {"id": 2, "name": "jacket", "srgb": "#2459A6"}
  ],
  "parts": {
    "head": {
      "faces": {
        "front": {
          "material_map": [[0]],
          "relief_map": [[0]],
          "features": ["glasses", "eyes", "mouth"]
        }
      },
      "silhouette_features": ["short_block_hair"]
    }
  }
}
```

Normative schemas must define the exact dimensions of every map, allowed integer ranges, feature enum, palette references, and maximum operation counts. All model output is validated again locally even when the provider supports structured output.

### 7.3 Recommended inference route

Use one constrained multimodal inference pass to produce semantic cues and per-face pixel/material/relief maps, followed by a deterministic local compiler. A bounded correction pass may be made only when local schema or semantic validation fails.

Do not generate six-view images in the MVP. They add cross-view inconsistency and require another uncertain image-to-geometry stage. Direct constrained maps make front/back inference explicit, testable, editable in fixtures, and provider-independent.

### 7.4 Provider abstraction

Define a provider interface similar to:

```python
class CharacterPlanner(Protocol):
    def plan(self, request: PlanRequest) -> CharacterPlan: ...
```

Each adapter declares whether it supports images, native structured output, seeds, and data-retention controls. Provider-specific credentials, base URLs, model names, and request options come from environment variables or config files—not source code.

An OpenAI adapter is a suitable reference implementation because its API accepts image input and schema-constrained structured output. Other providers can implement the same interface. Native structured output improves shape compliance but does not replace local validation.

## 8. Pipeline and architecture

```text
CLI/API request
  -> input and single-subject validation
  -> transient image normalization
  -> provider CharacterPlan generation
  -> local schema + semantic validation
  -> map cleanup and printability simplification
  -> deterministic occupancy-grid compiler
  -> exposed-face mesh extraction
  -> mesh cleanup and validation
  -> assembled GLB + PNG preview
  -> ZIP packaging
  -> transient image deletion
```

Recommended implementation:

- Python 3.12.
- Pydantic for request and intermediate schemas.
- NumPy for dense occupancy and material grids.
- Trimesh for mesh I/O, transforms, inspection, and GLB/STL export.
- Manifold3D as the robust mesh boolean backend when joint insertion is added.
- Pillow for image normalization.
- Typer for CLI.
- Optional FastAPI service sharing the same application layer.
- No Blender runtime or headless Blender dependency.

Dense detail grids are sufficient for the MVP: an 80 mm figure at 0.5 mm resolution has a small bounded volume per independently generated part. Sparse VDB storage is deferred until profiling proves it necessary.

## 9. CLI

Normative command:

```bash
text2model generate \
  --prompt "把照片里的人做成方块小人，保留黑框眼镜和蓝色夹克" \
  --image person.jpg \
  --height 80 \
  --seed 42 \
  --output ./result
```

Additional commands:

```bash
text2model validate ./result
text2model providers
text2model config check
```

Behavior:

- `--prompt` is required; other generation arguments have defaults.
- The command exits nonzero on any failed mandatory validation.
- No final STL ZIP is emitted on failure; diagnostics and safe intermediate metadata may be retained.
- The effective seed, provider, model version, schema version, and generator version are recorded.

## 10. HTTP API contract

The CLI is the MVP deliverable. The core must nevertheless expose a service layer compatible with this future API:

### `POST /v1/models`

Multipart request fields: `prompt`, optional `image`, optional `height_mm`, optional `seed`, optional `provider`, optional `model`.

Response: `202 Accepted` with `job_id`, effective `seed`, and status URL.

### `GET /v1/models/{job_id}`

States: `queued`, `analyzing`, `generating`, `validating`, `packaging`, `succeeded`, `failed`.

### `GET /v1/models/{job_id}/download`

Returns the ZIP only for a succeeded job.

## 11. Output package

```text
result.zip
  stl/
    head.stl
    torso.stl
    left_upper_arm.stl
    right_upper_arm.stl
    left_forearm.stl
    right_forearm.stl
    left_hand.stl
    right_hand.stl
    left_thigh.stl
    right_thigh.stl
    left_shin.stl
    right_shin.stl
    left_foot.stl
    right_foot.stl
  preview.glb
  preview.png
  character_plan.json
  material_grid.json.gz
  manifest.json
  validation_report.json
```

STL conventions:

- Millimeters.
- Z-up canonical world.
- Each STL is translated near its local origin and rotated to its recommended print orientation.
- `manifest.json` stores the exact local-to-assembled transform.
- Binary STL is the default.

The manifest includes part names, bounds, volume, recommended orientation, assembled transform, palette, file hashes, tool versions, provider/model identifiers, seed, and validation status.

## 12. Validation and failure policy

Every STL must pass all mandatory checks:

- Exactly one intended solid component unless the part specification explicitly permits otherwise.
- Watertight and edge-manifold.
- Consistent outward winding and positive volume.
- No self-intersections.
- No degenerate or zero-area faces.
- No disconnected floating voxels or internal shells.
- Bounding dimensions match the intended scale.
- Residual wall thickness is at least 1.2 mm.
- Relief line width is at least 0.8 mm and depth is at least 0.4 mm.
- Protected joint surfaces remain planar and unobstructed.
- Left/right and assembled transforms are valid.
- The assembled GLB reaches `height_mm ± 0.5 mm`.
- A reference slicer can import all STLs without repair warnings.

Automatic repair may weld duplicate vertices, remove duplicate/degenerate faces, orient faces, and remove unreachable internal cells. It must not silently alter recognizable features. If mandatory validation still fails, the job fails and the downloadable final package is withheld.

Because mesh self-intersection and wall-thickness checks can differ between libraries, acceptance tests must pin library versions and retain validation reports.

## 13. Privacy and logging

- Uploaded images are written only to a per-job temporary directory when necessary.
- They are deleted immediately after the provider call and single-subject checks complete, including on exceptions.
- Logs must not contain image bytes, base64 content, full prompts, API keys, or provider responses containing personal data.
- A redacted prompt hash may be logged for diagnostics.
- Generated artifacts are retained only according to deployer configuration.
- The documentation warns that external provider retention policies still apply and must be reviewed by the deployer.

## 14. Reproducibility

The local geometry compiler must be bitwise deterministic for the same validated `CharacterPlan`, generator version, and platform-independent numeric settings.

End-to-end reproduction requires:

- Effective seed.
- Exact provider and model/version.
- Original `CharacterPlan`.
- Schema and generator versions.
- Dependency lock file.

If a provider does not guarantee seeded determinism, the system must state that replaying the saved `CharacterPlan` reproduces geometry, while replaying the original prompt may not reproduce the same plan.

## 15. Acceptance test set

Minimum golden set: ten cases.

- Spider-Man.
- Iron Man.
- Four licensed personal photos covering different hair, glasses, facial hair, and clothing.
- Two original Chinese character descriptions.
- Two original English character descriptions.

For each case:

1. Generate all 14 STL parts and supporting files.
2. Pass every automated geometry rule.
3. Import every STL into the selected reference slicer without repair warnings.
4. Confirm correct assembly and scale in GLB.
5. Conduct blind human review for target-character recognition or preservation of the photo's requested signature features.

Recognition rubric:

- Famous character: at least 4 of 5 reviewers identify the intended character without seeing the prompt.
- Personal photo: at least 4 of 5 reviewers identify at least three requested signature attributes; recognizing the exact person is not required.
- Original prompt: at least 4 of 5 reviewers agree that all explicitly requested major colors, clothing items, and accessories are present.

Physical validation is required before MVP acceptance. The owner prints Spider-Man, Iron Man, and one photo-based character using a 0.4 mm nozzle and 0.2 mm layer height, then records slicer settings, failures, photos, and feature-legibility notes. Joint assembly is excluded until the joint library exists.

## 16. Milestones

### M0 — Geometry spike

- Hard-coded `CharacterPlan` fixtures.
- Occupancy-grid compiler and exposed-face mesher.
- One complete 14-part untextured figure.
- STL/GLB export and manifold validation.

Exit: canonical figure imports into the slicer without repair.

### M1 — Relief compiler

- Per-face material and relief maps.
- Raised, engraved, and compact silhouette features.
- Protected masks and printability cleanup.
- Spider-Man and Iron Man hand-authored fixtures.

Exit: both fixtures pass automated validation and preserve recognizable details.

### M2 — AI planner

- Provider protocol and first multimodal adapter.
- Chinese/English prompts, optional image, schema validation, and bounded retry.
- Single-subject rejection.
- Privacy cleanup and reproducibility metadata.

Exit: all ten golden cases generate without manual mesh editing.

### M3 — CLI MVP

- Final CLI workflow and ZIP package.
- Golden tests, failure diagnostics, version pinning, and documentation.
- Three owner-run physical print validations.

Exit: all automated and physical MVP acceptance criteria pass.

### Post-MVP

- Import positive/negative joint STL assets, define keep-out volumes, and insert them with Manifold booleans.
- Joint tolerances by printer/material profile.
- 3MF AMS material export from retained material grids.
- Web/API job service, model preview, and downloads.
- Conversational revisions, Windows, Docker, more body proportions, and non-humanoids.

## 17. Key risks and mitigations

| Risk | Mitigation |
|---|---|
| AI emits attractive but inconsistent sides | Constrained per-face maps, local schema validation, semantic checks, golden fixtures |
| Fine patterns disappear in FDM | Physical minimums, morphology-based thickening/merging, physical print tests |
| Relief damages future joints | Protected masks and reserved clearance volumes are first-class inputs |
| Provider changes break reproducibility | Save `CharacterPlan`, pin model/version where possible, deterministic local compiler |
| Too many tiny color regions hinder future AMS export | Four-color cap and connected-region simplification |
| Mesh becomes huge | Greedy coplanar face merging; add sparse grids only after profiling |
| Boolean insertion later becomes fragile | Require valid solids and use a robust manifold boolean backend |
| Personal photos leak through logs/temp files | Per-job temporary storage, immediate deletion, redacted logs, documented provider policy |

## 18. Technical decision record

1. **Direct structured surface maps over generated six-view images.** This removes an inconsistent image-generation stage and creates deterministic, testable geometry input.
2. **Occupancy-grid face extraction over marching cubes.** The desired form is axis-aligned voxel/block geometry, not a smoothed isosurface. Trimesh documents marching cubes as an un-smoothed isosurface conversion, while its voxel module also supports direct voxel representations and multibox construction: <https://trimesh.org/trimesh.voxel.html>.
3. **No OpenVDB in the MVP.** OpenVDB provides capable volume-to-mesh and mesh-to-volume tools, but the bounded per-part dense grids do not justify its build and deployment complexity yet: <https://www.openvdb.org/documentation/doxygen/structopenvdb_1_1v12__1_1_1tools_1_1VolumeToMesh.html>.
4. **Manifold backend reserved for joint insertion.** Trimesh exposes a Manifold boolean engine, allowing future joint assets to be unioned/subtracted without Blender: <https://trimesh.org/trimesh.boolean.html>.
5. **Structured multimodal provider output plus local validation.** Schema-constrained output can be used with image inputs, but semantic mistakes remain possible, so deterministic local validation is mandatory: <https://openai.com/index/introducing-structured-outputs-in-the-api/>.
