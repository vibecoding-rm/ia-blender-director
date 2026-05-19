from pathlib import Path
from unittest import TestCase

from PIL import Image

from ai_blender_director.critic import VisionCritic


class TestVisionCritic(TestCase):
    def setUp(self):
        self.test_dir = Path("test_critic_outputs")
        self.test_dir.mkdir(exist_ok=True)
        
        self.beauty_path = self.test_dir / "beauty.png"
        self.mask_path = self.test_dir / "mask.png"

    def tearDown(self):
        if self.beauty_path.exists():
            self.beauty_path.unlink()
        if self.mask_path.exists():
            self.mask_path.unlink()
        try:
            self.test_dir.rmdir()
        except OSError:
            pass

    def create_test_images(self, subject_rect: tuple[int, int, int, int], subject_color: tuple[int, int, int]):
        """Create beauty and mask images of size 100x100."""
        beauty = Image.new("RGB", (100, 100), color=(10, 10, 10))  # dark background
        mask = Image.new("L", (100, 100), color=0)
        
        x0, y0, w, h = subject_rect
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                beauty.putpixel((x, y), subject_color)
                mask.putpixel((x, y), 255)
                
        beauty.save(self.beauty_path)
        mask.save(self.mask_path)

    def test_distance_ok(self):
        # Subject is 40x40 = 1600 pixels = 16% of 10000 (>= 10%)
        self.create_test_images((30, 30, 40, 40), (200, 200, 200))
        critic = VisionCritic(self.beauty_path, self.mask_path)
        fb = critic.analyze_distance()
        self.assertIsNone(fb)

    def test_distance_too_far(self):
        # Subject is 20x20 = 400 pixels = 4% (< 10%)
        self.create_test_images((40, 40, 20, 20), (200, 200, 200))
        critic = VisionCritic(self.beauty_path, self.mask_path)
        fb = critic.analyze_distance()
        self.assertIsNotNone(fb)
        self.assertEqual(fb.category, "Distance")
        self.assertIn("4.0%", fb.message)

    def test_framing_ok(self):
        # Center of mass is at (50, 50), which is well inside the 20%-80% margin
        self.create_test_images((30, 30, 40, 40), (200, 200, 200))
        critic = VisionCritic(self.beauty_path, self.mask_path)
        fb = critic.analyze_framing()
        self.assertIsNone(fb)

    def test_framing_weak_edges(self):
        # Subject at top-left corner (0-10, 0-10) => center is (5, 5)
        # Margin is 20% of 100 = 20. So 5 < 20 (too far left, too high)
        self.create_test_images((0, 0, 10, 10), (200, 200, 200))
        critic = VisionCritic(self.beauty_path, self.mask_path)
        fb = critic.analyze_framing()
        self.assertIsNotNone(fb)
        self.assertIn("too far left", fb.message)
        self.assertIn("too high", fb.message)

    def test_lighting_ok(self):
        # Subject color (100, 100, 100) -> lum ~ 100 (> 40)
        self.create_test_images((30, 30, 40, 40), (100, 100, 100))
        critic = VisionCritic(self.beauty_path, self.mask_path)
        fb = critic.analyze_lighting()
        self.assertIsNone(fb)

    def test_lighting_too_dark(self):
        # Subject color (30, 30, 30) -> lum ~ 30 (< 40)
        self.create_test_images((30, 30, 40, 40), (30, 30, 30))
        critic = VisionCritic(self.beauty_path, self.mask_path)
        fb = critic.analyze_lighting()
        self.assertIsNotNone(fb)
        self.assertEqual(fb.category, "Lighting")
        self.assertIn("too dark", fb.message)

    def test_analyze_all(self):
        # A subject that is too far, too dark, and badly framed
        self.create_test_images((0, 0, 10, 10), (20, 20, 20))
        critic = VisionCritic(self.beauty_path, self.mask_path)
        feedbacks = critic.analyze()
        self.assertEqual(len(feedbacks), 3)
