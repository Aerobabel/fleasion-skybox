"""Render perspective views across Roblox cubemap joins, optionally before/after."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from check_seams import load_faces


def perspective(faces, yaw, pitch, width=640, height=360, field_of_view=100):
    yaw, pitch = np.radians([yaw, pitch])
    yy, xx = np.mgrid[:height, :width]
    extent = np.tan(np.radians(field_of_view / 2))
    sx = (2 * (xx + 0.5) / width - 1) * extent
    sy = (1 - 2 * (yy + 0.5) / height) * extent * height / width
    forward = np.array([np.sin(yaw) * np.cos(pitch), np.sin(pitch),
                        np.cos(yaw) * np.cos(pitch)])
    right = np.array([np.cos(yaw), 0, -np.sin(yaw)])
    up = np.cross(forward, right)
    rays = forward + sx[..., None] * right + sy[..., None] * up
    x, y, z = np.moveaxis(rays, -1, 0)
    dominant = np.argmax(np.abs(rays), axis=-1)
    output = np.zeros((height, width, 3), dtype=np.float64)
    # Inverse texture coordinates for Roblox's six named images.
    for face, axis, positive in (
        ('Lf', 0, True), ('Rt', 0, False), ('Up', 1, True),
        ('Dn', 1, False), ('Ft', 2, True), ('Bk', 2, False),
    ):
        mask = (dominant == axis) & ((rays[..., axis] >= 0) == positive)
        a, b, c = x[mask], y[mask], z[mask]
        scale = np.abs(rays[..., axis][mask])
        if face == 'Ft': u, v = a / scale, -b / scale
        elif face == 'Bk': u, v = -a / scale, -b / scale
        elif face == 'Lf': u, v = -c / scale, -b / scale
        elif face == 'Rt': u, v = c / scale, -b / scale
        elif face == 'Up': u, v = c / scale, -a / scale
        else: u, v = c / scale, a / scale
        image = faces[face].astype(np.float64)
        size = image.shape[0]
        px, py = (u + 1) * (size - 1) / 2, (v + 1) * (size - 1) / 2
        x0, y0 = np.floor(px).astype(int), np.floor(py).astype(int)
        x1, y1 = np.minimum(x0 + 1, size - 1), np.minimum(y0 + 1, size - 1)
        fx, fy = (px - x0)[:, None], (py - y0)[:, None]
        output[mask] = ((image[y0, x0] * (1 - fx) + image[y0, x1] * fx) * (1 - fy)
                        + (image[y1, x0] * (1 - fx) + image[y1, x1] * fx) * fy)
    return Image.fromarray(np.rint(np.clip(output, 0, 255)).astype(np.uint8))


def font(size):
    try:
        return ImageFont.truetype('DejaVuSans.ttf', size)
    except OSError:
        return ImageFont.load_default(size=size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'bundle' / 'Crossroads-Mira-Sky')
    parser.add_argument('--before', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    current = load_faces(args.folder)
    columns = [('BEFORE', load_faces(args.before)), ('CORRECTED', current)] if args.before else [('MIRA', current)]
    views = [('SIDE FACES', 45, 12), ('UPPER CORNER', -45, 42), ('LOWER CORNER', 135, -42)]
    sheet = Image.new('RGB', (640 * len(columns), 90 + len(views) * 392), '#101422')
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 12), 'MIRA / Roblox cubemap preview', font=font(24), fill='#f8e4a8')
    for col, (title, faces) in enumerate(columns):
        draw.text((col * 640 + 20, 52), title, font=font(19), fill='white')
        for row, (label, yaw, pitch) in enumerate(views):
            top = 90 + row * 392
            sheet.paste(perspective(faces, yaw, pitch), (col * 640, top))
            draw.text((col * 640 + 16, top + 365), label, font=font(15), fill='#bfc6da')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    print(args.output)


if __name__ == '__main__':
    main()
