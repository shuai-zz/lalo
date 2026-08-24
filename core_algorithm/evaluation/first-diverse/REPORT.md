# First diverse image-first evaluation

Date: 2026-08-24

## Setup

- Six generated, orthographic sheets ordered front, right, back, left.
- Sampling scale: 4 (256x256 skin atlas).
- Outputs: skin, six-panel review sheet, and self-contained GLB per sample.
- All six GLBs pass glTF Validator with zero errors and zero warnings.

## Results

| Sample | Result | Findings |
| --- | --- | --- |
| 01 baseline | Pass | Front, back, and side identity remain coherent. Small face and hoodie details survive sampling. |
| 02 long hair | Warning | Front and back hair texture survives, but the fixed cuboid body cannot express hair volume. Hair continuity from head onto side torso is weak. |
| 03 helmet | Pass | Dense high-contrast helmet and suit details survive well across all observed faces. |
| 04 long coat | Warning | Color and trim remain clear, but coat/skirt silhouette is flattened onto the standard torso and legs. |
| 05 complex pattern | Pass | High-contrast front, sleeve, and back patterns remain recognizable without obvious orientation errors. |
| 06 light clothing | Warning | The sample succeeds because of its gray contour, but light clothing has little separation from the white source background and is fragile under foreground detection. |

## Failure categories

1. **Background ambiguity** — light character colors are too close to the inferred sheet background.
2. **Non-cuboid silhouette loss** — hair, coats, skirts, hats, and armor volume are forced onto flat cuboid faces.
3. **Cross-part semantic continuity** — details spanning head/torso or torso/legs are sampled independently and can drift at seams.

No new left/right orientation, source-background edge, or GLB validity failures were observed in this set.

## Decision

The next focused algorithm change should replace the fixed RGB-distance foreground test with a border-connected background mask. This directly addresses the highest-risk reproducible failure while preserving white clothing enclosed by the character silhouette.

Geometry extensions for hair and clothing volume should remain a later experiment: the current texture-only pipeline is already useful for canonical block characters, and silhouette geometry is an independently testable concern.

## Generation prompt set

The six source sheets were generated with the built-in image generation tool. Every prompt required a pure white background; exactly four separated, identically scaled orthographic figures ordered front/right/back/left; strict classic block proportions; rectangular silhouettes; and no text, labels, shadows, or perspective. The character variants were:

1. short dark hair, teal hoodie, charcoal trousers;
2. long auburn hair, burgundy sweater, dark jeans;
3. blue-and-silver sci-fi helmet and utility suit;
4. long purple coat and dark skirt-like lower garment;
5. black-and-white geometric jacket with a red chest emblem;
6. pale blond hair and very light clothing with a thin gray contour.
