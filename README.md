# MIRA Twilight Skybox for Crossroads

![Front skybox face: a golden smiley sun above MIRA in a twilight sky](bundle/Crossroads-Mira-Sky/Ft.png)

A six-face skybox for [Roblox Crossroads](https://www.roblox.com/games/1818/Crossroads), installed locally with [Fleasion](https://github.com/fleasion/Fleasion). A twilight cloud panorama wraps around the player; a smiling golden sun and the exact word **MIRA** appear on the front face. The six 512-pixel PNGs are included. Python's standard library is enough to install and verify them.

## Live test

On 24 September 2026, Fleasion v2.4.0 captured the six `null_plainsky512_*.jpg` requests below during a fresh Crossroads launch. The prior profile used IDs from an older third-party [Crossroads sky snapshot](https://github.com/Dekkonot/crossroads-rojo/blob/fb6e6bbbbbeff1d32458fd617ec409929d301d94/src/Lighting/Sky.model.json); those IDs were not requested in this session. The updated ID profile was tested in game with a checkerboard calibration sky before creating this artwork.

| Face | Fleasion asset ID | Bundled texture |
|---|---:|---|
| Back | 12221870 | `Bk.png` |
| Down | 12221876 | `Dn.png` |
| Left | 12221895 | `Lf.png` |
| Right | 12221908 | `Rt.png` |
| Front | 12221889 | `Ft.png` |
| Up | 12221917 | `Up.png` |

The profile matches asset IDs, so it may also recolor the default sky in other Roblox experiences while enabled. Disable the profile and clear Roblox's cache to restore the usual sky.

## Install

1. Install Python 3.10+ and Fleasion from its [official releases](https://github.com/fleasion/Fleasion/releases). Run Fleasion once, then close Fleasion and Roblox Player.
2. From this repository, verify and install the bundle:

   ```powershell
   python skybox.py verify
   python -m unittest discover -s tests -v
   python skybox.py install
   ```

3. Start Fleasion and enable **Crossroads-Mira-Sky** in its Dashboard. Disable any older skybox profile that targets the same six IDs. In Fleasion, clear the Roblox cache.
4. Launch Crossroads through the Fleasion-configured Roblox Player. Look toward the front sky face for the smiley and **MIRA**, then look around to check the other faces.
5. Confirm the installed files and enabled profile:

   ```powershell
   python skybox.py installed
   ```

The installer writes only its JSON profile and six PNGs into Fleasion's `configs` folder. It refuses to overwrite an existing profile. Fleasion configures the proxy and Player trust bundle separately; this project does not change them. On macOS or Linux, use `python3` and pass `--home` if Fleasion stores data outside the default location.

If the previous **Crossroads-Diagnostic-Sky** profile is still enabled, turn it off in Fleasion before installing this one. The new name lets both profiles coexist without overwriting personal configuration.

## Verify the live result

Enable Fleasion's Cache Scraper before launching Crossroads. After clearing the cache and joining, search the scraper for `12221`: all six IDs above should appear. The visible sky should be twilight clouds rather than the default blue clouds. The front face should show an upright smiley and the exact word **MIRA**.

`skybox.py probe` is an optional direct byte test through Fleasion's local proxy. It needs the proxy port and Fleasion's **public** CA certificate:

```powershell
python skybox.py probe --ca "C:\path\to\ca.crt" --port 58443
```

The no-cookie probe returned HTTP 404 during the September 2026 test, even though the in-game checkerboard and scraper confirmed the replacement. A failed probe alone does not establish failure in Player. Do not share Roblox cookies, auth tickets, private CA keys, or full proxy logs when reporting a test.

## Artwork and regeneration

The source panorama and transparent MIRA emblem are in [`art/`](art/). They were generated with OpenAI's built-in image generation tool; the exact prompts are recorded in [`art/README.md`](art/README.md). The optional [`art/render_skybox.py`](art/render_skybox.py) projects the panorama into six faces and composites the emblem on the front face. It requires Pillow and NumPy:

```powershell
python -m pip install pillow numpy
python art/render_skybox.py
python skybox.py build
python skybox.py verify
```

If you regenerate any face, update its fixed SHA-256 in `skybox.py` after reviewing the result. Consumers need only the pre-rendered `bundle/` files and the standard library. The original Roblox sky images are not included.

## Remove

Disable **Crossroads-Mira-Sky** in Fleasion, close Fleasion and Roblox Player, then run:

```powershell
python skybox.py uninstall
```

The command removes only files that still match this bundle and refuses to remove a folder containing extra files. Clear Roblox's cache in Fleasion afterward.
