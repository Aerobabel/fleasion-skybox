"""Project the authored panorama into Roblox skybox faces.

This optional art build needs Pillow and NumPy. The install/verify script uses
the pre-rendered PNGs in bundle and has no third-party dependencies.
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parent
FACES = ('Bk', 'Dn', 'Lf', 'Rt', 'Ft', 'Up')


def wrap_panorama(image):
    """Blend the generated panorama's two ends so longitude wraps cleanly."""
    pixels = np.asarray(image.convert('RGB'), dtype=np.float32).copy()
    width = pixels.shape[1]
    band = min(64, width // 16)
    for offset in range(band):
        weight = (band - offset) / band
        left = pixels[:, offset].copy()
        right = pixels[:, width - 1 - offset].copy()
        shared = (left + right) / 2
        pixels[:, offset] = left * (1 - weight) + shared * weight
        pixels[:, width - 1 - offset] = right * (1 - weight) + shared * weight
    return np.clip(pixels, 0, 255).astype(np.uint8)


def directions(face, size):
    yy, xx = np.mgrid[:size, :size]
    u = 2 * (xx + 0.5) / size - 1
    v = 2 * (yy + 0.5) / size - 1
    one = np.ones_like(u)
    if face == 'Ft':
        return u, -v, one
    if face == 'Bk':
        return -u, -v, -one
    if face == 'Rt':
        return one, -v, -u
    if face == 'Lf':
        return -one, -v, u
    if face == 'Up':
        return u, one, v
    if face == 'Dn':
        return u, -one, -v
    raise ValueError(face)


def render_face(panorama, face, size):
    dx, dy, dz = directions(face, size)
    radius = np.sqrt(dx * dx + dy * dy + dz * dz)
    longitude = np.arctan2(dx, dz)
    latitude = np.arcsin(dy / radius)
    height, width = panorama.shape[:2]
    px = (longitude / (2 * np.pi) + 0.5) * width - 0.5
    py = (0.5 - latitude / np.pi) * height - 0.5
    x0 = np.floor(px).astype(np.int64)
    y0 = np.floor(py).astype(np.int64)
    fx = (px - x0)[..., None]
    fy = (py - y0)[..., None]
    x1 = (x0 + 1) % width
    x0 %= width
    y1 = np.clip(y0 + 1, 0, height - 1)
    y0 = np.clip(y0, 0, height - 1)
    top = panorama[y0, x0] * (1 - fx) + panorama[y0, x1] * fx
    bottom = panorama[y1, x0] * (1 - fx) + panorama[y1, x1] * fx
    pixels = top * (1 - fy) + bottom * fy
    return Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8), 'RGB')


def add_emblem(front, source):
    size = front.width
    emblem = source.convert('RGBA')
    emblem.thumbnail((round(size * 0.77), round(size * 0.77)), Image.Resampling.LANCZOS)
    x = (size - emblem.width) // 2
    y = round(size * 0.12)
    canvas = front.convert('RGBA')
    # A soft dark halo keeps the gold lettering legible over bright clouds.
    shadow = Image.new('RGBA', canvas.size)
    alpha = emblem.getchannel('A').filter(ImageFilter.GaussianBlur(size * 0.023))
    shade = Image.new('RGBA', emblem.size, (17, 22, 57, 0))
    shade.putalpha(alpha.point(lambda value: round(value * 0.6)))
    shadow.alpha_composite(shade, (x + 2, y + 5))
    canvas = Image.alpha_composite(canvas, shadow)
    canvas.alpha_composite(emblem, (x, y))
    return canvas.convert('RGB')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size', type=int, default=512)
    parser.add_argument('--output', type=Path,
                        default=ROOT.parent / 'bundle' / 'Crossroads-Mira-Sky')
    args = parser.parse_args()
    if not 128 <= args.size <= 2048:
        parser.error('size must be between 128 and 2048 pixels')
    panorama = wrap_panorama(Image.open(ROOT / 'twilight-panorama.png'))
    emblem = Image.open(ROOT / 'mira-emblem.png')
    args.output.mkdir(parents=True, exist_ok=True)
    for face in FACES:
        texture = render_face(panorama, face, args.size)
        if face == 'Ft':
            texture = add_emblem(texture, emblem)
        path = args.output / f'{face}.png'
        texture.save(path, optimize=True)
        print(f'{face}: {path}')


if __name__ == '__main__':
    main()
