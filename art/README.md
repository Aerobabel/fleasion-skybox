# MIRA skybox artwork

`twilight-panorama.png` and `mira-emblem.png` were generated with OpenAI's built-in `image_gen` tool on 24 September 2026. `render_skybox.py` performs a deterministic equirectangular-to-cubemap projection, blends the horizontal panorama seam, and places the transparent emblem on the front face. The six rendered 512-pixel PNGs are committed in `bundle/Crossroads-Mira-Sky/`.

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
python skybox.py build
```

After reviewing regenerated images, replace their fixed SHA-256 values in `skybox.py`, then run `python skybox.py verify` and the unit tests.
