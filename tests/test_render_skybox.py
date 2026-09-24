"""Optional artwork checks; install Pillow and NumPy to run these."""

from pathlib import Path
import unittest

try:
    import numpy as np
    from PIL import Image
    from art.check_seams import EDGE_PAIRS, check, load_faces
    from art.render_skybox import FACES, render_face, wrap_panorama
    ART_DEPS = True
except ImportError:
    ART_DEPS = False

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(ART_DEPS, 'Optional artwork tests require Pillow and NumPy')
class CubemapTests(unittest.TestCase):
    def setUp(self):
        self.faces = load_faces(ROOT / 'bundle' / 'Crossroads-Mira-Sky')

    def test_all_twelve_roblox_edges_match_exactly(self):
        report = check(self.faces)
        self.assertEqual(report['status'], 'PASS', report['pairs'])
        self.assertEqual(report['edge_pairs'], 12)

    def test_all_eight_three_face_corners_match(self):
        ends = {'top': ('tl', 'tr'), 'bottom': ('bl', 'br'),
                'left': ('tl', 'bl'), 'right': ('tr', 'br')}
        groups = [{(face, corner)} for face in self.faces for corner in ('tl', 'tr', 'bl', 'br')]
        for a, side, b, other_side, reverse in EDGE_PAIRS:
            other_ends = ends[other_side][::-1] if reverse else ends[other_side]
            for ac, bc in zip(ends[side], other_ends):
                ga = next(group for group in groups if (a, ac) in group)
                gb = next(group for group in groups if (b, bc) in group)
                if ga is not gb:
                    ga.update(gb)
                    groups.remove(gb)
        self.assertEqual(len(groups), 8)
        coordinates = {'tl': (0, 0), 'tr': (0, -1), 'bl': (-1, 0), 'br': (-1, -1)}
        for group in groups:
            self.assertEqual(len(group), 3)
            colors = {tuple(self.faces[face][coordinates[corner]]) for face, corner in group}
            self.assertEqual(len(colors), 1)

    def test_swapped_lateral_faces_are_detected(self):
        self.faces['Lf'], self.faces['Rt'] = self.faces['Rt'], self.faces['Lf']
        self.assertEqual(check(self.faces)['status'], 'FAIL')

    def test_wrong_cap_rotation_is_detected(self):
        self.faces['Up'] = np.rot90(self.faces['Up'])
        self.assertEqual(check(self.faces)['status'], 'FAIL')

    def test_renderer_preserves_edges_on_a_detailed_panorama(self):
        rng = np.random.default_rng(7)
        source = Image.fromarray(rng.integers(0, 256, (128, 256, 3), dtype=np.uint8))
        panorama = wrap_panorama(source)
        faces = {face: np.asarray(render_face(panorama, face, 65)) for face in FACES}
        self.assertEqual(check(faces)['status'], 'PASS')
        np.testing.assert_array_equal(panorama[:, 0], panorama[:, -1])
        self.assertTrue(np.all(panorama[0] == panorama[0, 0]))
        self.assertTrue(np.all(panorama[-1] == panorama[-1, 0]))


if __name__ == '__main__':
    unittest.main()
