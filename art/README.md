# MIRA skybox artwork

`twilight-panorama.png` and `mira-emblem.png` were generated with OpenAI's built-in `image_gen` tool on 24 September 2026. `render_skybox.py` performs a deterministic equirectangular-to-cubemap projection, blends the horizontal panorama wrap and poles, and places the transparent emblem on the front face. The six rendered 512-pixel PNGs are committed in `bundle/Crossroads-Mira-Sky/`.

## Roblox orientation and seam checks

The original export followed a generic front/right/back/left cube layout. Roblox instead joins the images horizontally in the order **Ft → Lf → Bk → Rt**. The Up and Down images also need the corresponding quarter-turns. The corrected `directions()` function implements these orientations directly in panorama coordinates; do not rotate the exported files again.

References used:

- [The user's Bimbocore Glam v1.2 example](https://github.com/BuyKevin/rivals-bimbocore-glam-pack/blob/main/CHANGELOG_v1.2.md): Roblox remapping and cap rotations, with separate CDN images for each face.
- [Roblox staff's Custom Skyboxes 101](https://devforum.roblox.com/t/custom-skyboxes-101/2849003): the `pz/nz/nx/px` assignments and Up/Down rotations for Jaxry's converter.
- [Jaxry's panorama-to-cubemap](https://github.com/jaxry/panorama-to-cubemap): a reference for the cubemap direction convention. This repository retains its own NumPy renderer.

The 12 edge pairings in `check_seams.py` were independently confirmed against the six original Roblox `null_plainsky512` assets. Those reference images are not distributed here. The old MIRA export had mismatches at all 12 joins, with a maximum channel jump of 167/255. The corrected export has **zero** mismatched edge pixels and matching triplets at all eight cube corners.

Shared borders now sample identical directions, instead of two offset pixel-center rays. The checker uses a fixed Roblox adjacency table independent of the projection code. Regression tests also deliberately swap lateral faces or rotate a cap to verify that these errors are detected. A noisy synthetic panorama checks the renderer itself.

[`seam-comparison.png`](seam-comparison.png) shows perspective views across side joins, an upper corner, and a lower corner. [`seam-report.json`](seam-report.json) contains the full numerical result. These are offline checks; a fresh Player test must clear the previously cached textures.

## Generation prompts

Panorama:

> Use case: stylized-concept. Asset type: panoramic source artwork for a six-face Roblox skybox. Create a wide 360-degree fantasy twilight sky panorama with luminous soft rose-gold cloud banks low in the frame, serene cobalt and indigo open sky above, subtle scattered stars, atmospheric depth, painterly realism, polished game-environment quality. The sky must fill the entire image, with no ground, buildings, people, sun, moon, symbols, text, logos, or watermark. Keep the left and right edges visually similar for a horizontal loop; make the very top and bottom regions relatively smooth for cubemap projection. Wide panoramic 2:1 composition.

Emblem:

> Use case: stylized-concept. Asset type: transparent centerpiece decal for the front face of a Roblox skybox. A single joyful golden celestial smiley face, clean round shape, two friendly dark oval eyes and a clear curved smile, warm luminous rim and subtle painterly glow. Directly below, the exact word "MIRA" in large readable elegant luminous gold capital letters (M I R A, exactly four letters). Center the smiley and word together, with generous empty transparent margin around them. Polished fantasy game art that will sit over an indigo twilight sky. Truly transparent background with alpha, no sky or checkerboard, no other words, no watermark.

## Rebuild

The renderer requires Pillow and NumPy. The installer does not.

```powershell
python -m pip install pillow numpy
python art/render_skybox.py
python art/check_seams.py --report art/seam-report.json
python art/preview_skybox.py --output preview.png
python skybox.py build
```

After reviewing regenerated images, replace their fixed SHA-256 values in `skybox.py`, then run `python skybox.py verify` and the unit tests. Commit the reviewed artwork, pin `ARTWORK_REVISION` to that commit, and run `python skybox.py build` again so the public CDN profile requests the corrected files.
