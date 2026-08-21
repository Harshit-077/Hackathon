"""Unit tests for confidence fusion."""

import unittest

from backend.engine.confidence import (
    WEIGHT_RECENCY,
    WEIGHT_SEMANTIC,
    WEIGHT_SPATIAL,
    fuse_confidence,
    fuse_with_llm_raw,
    recency_bonus,
    semantic_match_score,
)


class TestSemanticMatchScore(unittest.TestCase):
    def test_exact_id_match(self):
        self.assertEqual(semantic_match_score("revenue", "revenue", "Revenue"), 1.0)

    def test_label_substring_match(self):
        self.assertEqual(
            semantic_match_score("geo", "geographic", "Geographic distribution"), 0.8
        )

    def test_no_match(self):
        self.assertEqual(semantic_match_score("revenue", "users", "Users"), 0.0)

    def test_none_entity(self):
        self.assertEqual(semantic_match_score(None, "revenue", "Revenue"), 0.0)


class TestRecencyBonus(unittest.TestCase):
    def test_matches_last_resolved(self):
        self.assertEqual(recency_bonus("revenue", "revenue"), 1.0)

    def test_no_match(self):
        self.assertEqual(recency_bonus("users", "revenue"), 0.0)

    def test_no_history(self):
        self.assertEqual(recency_bonus("revenue", None), 0.0)


class TestFuseConfidence(unittest.TestCase):
    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(WEIGHT_SPATIAL + WEIGHT_SEMANTIC + WEIGHT_RECENCY, 1.0)

    def test_perfect_scores(self):
        self.assertAlmostEqual(fuse_confidence(1.0, 1.0, 1.0), 1.0)

    def test_zero_scores(self):
        self.assertAlmostEqual(fuse_confidence(0.0, 0.0, 0.0), 0.0)

    def test_spatial_only(self):
        expected = WEIGHT_SPATIAL * 1.0
        self.assertAlmostEqual(fuse_confidence(1.0, 0.0, 0.0), expected)

    def test_semantic_only(self):
        expected = WEIGHT_SEMANTIC * 1.0
        self.assertAlmostEqual(fuse_confidence(0.0, 1.0, 0.0), expected)

    def test_recency_only(self):
        expected = WEIGHT_RECENCY * 1.0
        self.assertAlmostEqual(fuse_confidence(0.0, 0.0, 1.0), expected)

    def test_mixed_scores(self):
        # spatial=1.0, semantic=0.8, recency=0.0
        expected = WEIGHT_SPATIAL * 1.0 + WEIGHT_SEMANTIC * 0.8 + WEIGHT_RECENCY * 0.0
        self.assertAlmostEqual(fuse_confidence(1.0, 0.8, 0.0), expected)

    def test_clamped_to_unit_interval(self):
        self.assertLessEqual(fuse_confidence(2.0, 2.0, 2.0), 1.0)
        self.assertGreaterEqual(fuse_confidence(-1.0, -1.0, -1.0), 0.0)


class TestFuseWithLlmRaw(unittest.TestCase):
    def test_blends_llm_confidence(self):
        base = fuse_confidence(1.0, 1.0, 1.0)
        result = fuse_with_llm_raw(1.0, 1.0, 1.0, 0.5)
        expected = 0.7 * base + 0.3 * 0.5
        self.assertAlmostEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
