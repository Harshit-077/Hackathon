"""Temporal object tracking — frames are not independent images."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


def _iou(a: dict[str, float], b: dict[str, float]) -> float:
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    ix1, iy1 = max(a["x"], b["x"]), max(a["y"], b["y"])
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union else 0.0


def _center(b: dict[str, float]) -> tuple[float, float]:
    return b["x"] + b["w"] / 2.0, b["y"] + b["h"] / 2.0


@dataclass
class TrackedObject:
    object_id: str
    label: str
    confidence: float
    first_seen: float
    last_seen: float
    bbox: dict[str, float]
    velocity: dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    track_age: int = 1
    hits: int = 1
    missed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "label": self.label,
            "confidence": self.confidence,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "bbox": self.bbox,
            "velocity": self.velocity,
            "track_age": self.track_age,
            "hits": self.hits,
        }


class ObjectTracker:
    def __init__(self, iou_threshold: float = 0.35, max_missed: int = 8) -> None:
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self._tracks: dict[str, TrackedObject] = {}
        self._counters: dict[str, int] = {}

    def update(self, detections: list[dict[str, Any]], now: float | None = None) -> list[dict[str, Any]]:
        now = now if now is not None else time.time()
        unmatched = list(range(len(detections)))
        assigned: dict[int, str] = {}

        # greedy IoU match by label
        for tid, track in self._tracks.items():
            best_i, best_iou = None, self.iou_threshold
            for i in unmatched:
                det = detections[i]
                if det.get("label", "").lower() != track.label.lower():
                    continue
                bbox = det.get("bbox") or {}
                iou = _iou(track.bbox, bbox)
                if iou > best_iou:
                    best_iou, best_i = iou, i
            if best_i is not None:
                assigned[best_i] = tid
                unmatched.remove(best_i)

        seen_ids = set()
        for i, det in enumerate(detections):
            bbox = det.get("bbox") or {"x": 0, "y": 0, "w": 0, "h": 0}
            conf = float(det.get("confidence") or 0)
            label = str(det.get("label") or "object")
            if i in assigned:
                track = self._tracks[assigned[i]]
                cx, cy = _center(bbox)
                pcx, pcy = _center(track.bbox)
                dt = max(1e-3, now - track.last_seen)
                track.velocity = {"x": (cx - pcx) / dt, "y": (cy - pcy) / dt}
                track.bbox = bbox
                track.confidence = conf
                track.last_seen = now
                track.track_age += 1
                track.hits += 1
                track.missed = 0
                seen_ids.add(track.object_id)
            else:
                slug = "".join(ch if ch.isalnum() else "_" for ch in label.lower())
                self._counters[slug] = self._counters.get(slug, 0) + 1
                oid = f"obj_{slug}_{self._counters[slug]:02d}"
                self._tracks[oid] = TrackedObject(
                    object_id=oid,
                    label=label,
                    confidence=conf,
                    first_seen=now,
                    last_seen=now,
                    bbox=bbox,
                )
                seen_ids.add(oid)

        stale = []
        for tid, track in self._tracks.items():
            if tid not in seen_ids:
                track.missed += 1
                if track.missed > self.max_missed:
                    stale.append(tid)
        for tid in stale:
            self._tracks.pop(tid, None)

        return [t.to_dict() for t in self._tracks.values() if t.missed == 0]

    @property
    def tracks(self) -> list[TrackedObject]:
        return list(self._tracks.values())
