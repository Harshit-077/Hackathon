"""
Spatial scoring — deterministic pointer-to-element distance scoring.

Pure math, unit-testable. No ML, no gaze tracking.
"""

from __future__ import annotations

import math
from typing import Any


def _distance_to_bbox(px: float, py: float, bbox: dict[str, float]) -> float:
    """Euclidean distance from point to nearest edge/corner of bounding box."""
    x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
    nearest_x = max(x, min(px, x + w))
    nearest_y = max(y, min(py, y + h))
    return math.hypot(px - nearest_x, py - nearest_y)


def _point_inside_bbox(px: float, py: float, bbox: dict[str, float]) -> bool:
    x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
    return x <= px <= x + w and y <= py <= y + h


def spatial_score(
    pointer_x: float,
    pointer_y: float,
    bbox: dict[str, float],
    max_distance: float = 400.0,
) -> float:
    """
    Score how well a pointer position aligns with an element bounding box.

    Returns:
        1.0 if pointer is inside the bbox.
        Decays linearly to 0.0 as distance approaches max_distance.
    """
    if _point_inside_bbox(pointer_x, pointer_y, bbox):
        return 1.0

    dist = _distance_to_bbox(pointer_x, pointer_y, bbox)
    if dist >= max_distance:
        return 0.0

    return 1.0 - (dist / max_distance)


def score_all_elements(
    pointer_x: float,
    pointer_y: float,
    elements: list[dict[str, Any]],
    max_distance: float = 400.0,
) -> list[tuple[str, float]]:
    """
    Score every element in ui_context against the pointer position.

    Returns:
        List of (element_id, spatial_score) sorted descending by score.
    """
    scored: list[tuple[str, float]] = []
    for el in elements:
        bbox = el.get("bbox")
        if not bbox:
            scored.append((el["id"], 0.0))
            continue
        score = spatial_score(pointer_x, pointer_y, bbox, max_distance)
        scored.append((el["id"], score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored
