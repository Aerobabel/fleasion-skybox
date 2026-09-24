"""Check all 12 shared edges in Roblox's skybox layout (Pillow and NumPy)."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


# Independently established from Roblox's six original null_plainsky textures.
# Each tuple is (face, edge, neighbor, neighbor edge, reverse neighbor pixels).
# This table intentionally does not derive its topology from the renderer.
EDGE_PAIRS = (
    ('Bk', 'top', 'Up', 'left', False),
    ('Bk', 'bottom', 'Dn', 'left', True),
    ('Bk', 'left', 'Lf', 'right', False),
    ('Bk', 'right', 'Rt', 'left', False),
    ('Ft', 'top', 'Up', 'right', True),
    ('Ft', 'bottom', 'Dn', 'right', False),
    ('Ft', 'left', 'Rt', 'right', False),
    ('Ft', 'right', 'Lf', 'left', False),
    ('Lf', 'top', 'Up', 'top', True),
    ('Lf', 'bottom', 'Dn', 'bottom', True),
    ('Rt', 'top', 'Up', 'bottom', False),
    ('Rt', 'bottom', 'Dn', 'top', False),
)


def load_faces(folder):
    faces = {face: np.asarray(Image.open(folder / f'{face}.png').convert('RGB'))
             for face in ('Bk', 'Dn', 'Ft', 'Lf', 'Rt', 'Up')}
    shapes = {image.shape for image in faces.values()}
    if len(shapes) != 1 or next(iter(shapes))[0] != next(iter(shapes))[1]:
        raise ValueError('All six skybox faces must have the same square size.')
    return faces


def edge(image, side):
    return {'top': image[0], 'bottom': image[-1],
            'left': image[:, 0], 'right': image[:, -1]}[side]


def check(faces):
    pairs = []
    for face, side, neighbor, other_side, reverse in EDGE_PAIRS:
        a = edge(faces[face], side).astype(np.int16)
        b = edge(faces[neighbor], other_side).astype(np.int16)
        if reverse:
            b = b[::-1]
        difference = np.abs(a - b)
        pairs.append({
            'join': f'{face}.{side} / {neighbor}.{other_side}',
            'reverse_neighbor': reverse,
            'max_channel_difference': int(difference.max()),
            'mean_channel_difference': round(float(difference.mean()), 6),
            'mismatched_pixels': int(np.any(difference, axis=1).sum()),
        })
    maximum = max(pair['max_channel_difference'] for pair in pairs)
    return {'status': 'PASS' if maximum == 0 else 'FAIL',
            'edge_pairs': len(pairs),
            'face_size': next(iter(faces.values())).shape[0],
            'max_channel_difference': maximum,
            'pairs': pairs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, nargs='?',
                        default=Path(__file__).resolve().parents[1] / 'bundle' / 'Crossroads-Mira-Sky')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = check(load_faces(args.folder))
    serialized = json.dumps(result, indent=2) + '\n'
    if args.report:
        args.report.write_text(serialized, encoding='utf-8')
    print(serialized, end='')
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
