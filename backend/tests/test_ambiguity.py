"""Unit tests for ambiguity detection."""

import unittest

from backend.engine.ambiguity import (
    detect_ambiguity,
    detect_speech_spatial_conflict,
)


class TestDetectAmbiguity(unittest.TestCase):
    def test_confident_single_candidate(self):
        candidates = [{"element_id": "revenue", "score": 0.85, "reason": "pointer on element"}]
        is_amb, reason = detect_ambiguity(candidates)
        self.assertFalse(is_amb)

    def test_low_confidence(self):
        candidates = [{"element_id": "revenue", "score": 0.2, "reason": "low signal"}]
        is_amb, reason = detect_ambiguity(candidates)
        self.assertTrue(is_amb)
        self.assertIn("below threshold", reason)

    def test_close_top_two(self):
        candidates = [
            {"element_id": "revenue", "score": 0.55, "reason": "nearby"},
            {"element_id": "users", "score": 0.50, "reason": "nearby"},
        ]
        is_amb, reason = detect_ambiguity(candidates)
        self.assertTrue(is_amb)
        self.assertIn("too close", reason)

    def test_clear_gap(self):
        candidates = [
            {"element_id": "revenue", "score": 0.85, "reason": "pointer on element"},
            {"element_id": "users", "score": 0.30, "reason": "far"},
        ]
        is_amb, _ = detect_ambiguity(candidates)
        self.assertFalse(is_amb)

    def test_empty_candidates(self):
        is_amb, reason = detect_ambiguity([])
        self.assertTrue(is_amb)
        self.assertEqual(reason, "no candidates")


class TestSpeechSpatialConflict(unittest.TestCase):
    ELEMENTS = [
        {"id": "revenue", "label": "Revenue", "bbox": {"x": 0, "y": 0, "w": 200, "h": 100}},
        {"id": "users", "label": "Users", "bbox": {"x": 300, "y": 0, "w": 200, "h": 100}},
    ]

    def test_conflict_detected(self):
        has, msg, ids = detect_speech_spatial_conflict(
            "revenue", 1.0, "users", self.ELEMENTS
        )
        self.assertTrue(has)
        self.assertIn("Revenue", msg)
        self.assertIn("Users", msg)
        self.assertEqual(set(ids), {"revenue", "users"})

    def test_no_conflict_when_agree(self):
        has, _, _ = detect_speech_spatial_conflict(
            "revenue", 1.0, "revenue", self.ELEMENTS
        )
        self.assertFalse(has)

    def test_no_conflict_weak_semantic(self):
        has, _, _ = detect_speech_spatial_conflict(
            "revenue", 0.3, "users", self.ELEMENTS
        )
        self.assertFalse(has)


if __name__ == "__main__":
    unittest.main()
