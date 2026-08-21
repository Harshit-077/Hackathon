"""Engine confidence tests (root test suite)."""

from backend.engine.confidence import fuse_confidence, WEIGHT_SPATIAL, WEIGHT_SEMANTIC


def test_fuse_confidence_weights():
    assert abs(WEIGHT_SPATIAL + WEIGHT_SEMANTIC + 0.20 - 1.0) < 0.001


def test_perfect_fusion():
    assert fuse_confidence(1.0, 1.0, 1.0) == 1.0
