"""Unit tests for spatial scoring."""

import unittest

from backend.engine.spatial_scoring import spatial_score, score_all_elements


class TestSpatialScore(unittest.TestCase):
    BBOX = {"x": 100, "y": 100, "w": 200, "h": 100}

    def test_point_inside_bbox(self):
        self.assertEqual(spatial_score(150, 150, self.BBOX), 1.0)

    def test_point_at_center(self):
        self.assertEqual(spatial_score(200, 150, self.BBOX), 1.0)

    def test_point_far_away(self):
        score = spatial_score(1000, 1000, self.BBOX, max_distance=400)
        self.assertEqual(score, 0.0)

    def test_point_just_outside(self):
        score = spatial_score(50, 150, self.BBOX, max_distance=400)
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)

    def test_monotonic_decay(self):
        close = spatial_score(80, 150, self.BBOX, max_distance=400)
        far = spatial_score(0, 150, self.BBOX, max_distance=400)
        self.assertGreater(close, far)


class TestScoreAllElements(unittest.TestCase):
    ELEMENTS = [
        {"id": "revenue", "bbox": {"x": 0, "y": 0, "w": 200, "h": 100}},
        {"id": "users", "bbox": {"x": 300, "y": 0, "w": 200, "h": 100}},
        {"id": "churn", "bbox": {"x": 600, "y": 0, "w": 200, "h": 100}},
    ]

    def test_sorted_descending(self):
        scores = score_all_elements(100, 50, self.ELEMENTS)
        self.assertEqual(scores[0][0], "revenue")
        self.assertGreater(scores[0][1], scores[1][1])

    def test_pointer_on_second_element(self):
        scores = score_all_elements(400, 50, self.ELEMENTS)
        self.assertEqual(scores[0][0], "users")


if __name__ == "__main__":
    unittest.main()
