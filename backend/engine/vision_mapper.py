"""Vision coordinate mapping — raw camera pixels ↔ normalized ↔ displayed.

Independent of UI framework. Unit-testable. Never assumes a fixed resolution.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MapperConfig:
    mirrored: bool = True
    object_fit: str = "cover"  # cover | contain


@dataclass
class Size:
    width: float
    height: float


def normalize_bbox(
    x: float, y: float, w: float, h: float, frame: Size
) -> dict[str, float]:
    fw = max(frame.width, 1.0)
    fh = max(frame.height, 1.0)
    return {"x": x / fw, "y": y / fh, "width": w / fw, "height": h / fh}


def bbox_center(nb: dict[str, float]) -> dict[str, float]:
    return {"x": nb["x"] + nb["width"] / 2.0, "y": nb["y"] + nb["height"] / 2.0}


def camera_to_display_normalized(nx: float, ny: float, mirrored: bool) -> tuple[float, float]:
    """Mirror X only when the preview is CSS-mirrored. Never mirror Y."""
    dx = (1.0 - nx) if mirrored else nx
    return dx, ny


def visible_video_rect(frame: Size, element: Size, object_fit: str) -> dict[str, float]:
    """
    Compute the displayed video rectangle inside a DOM element (object-fit).
    Returns {x, y, w, h} in element-local pixels (letterbox origin).
    """
    if frame.width <= 0 or frame.height <= 0 or element.width <= 0 or element.height <= 0:
        return {"x": 0, "y": 0, "w": element.width, "h": element.height}

    frame_ar = frame.width / frame.height
    el_ar = element.width / element.height

    if object_fit == "contain":
        if frame_ar > el_ar:
            w = element.width
            h = element.width / frame_ar
            return {"x": 0, "y": (element.height - h) / 2.0, "w": w, "h": h}
        h = element.height
        w = element.height * frame_ar
        return {"x": (element.width - w) / 2.0, "y": 0, "w": w, "h": h}

    # cover — crop overflow
    if frame_ar > el_ar:
        h = element.height
        w = element.height * frame_ar
        return {"x": (element.width - w) / 2.0, "y": 0, "w": w, "h": h}
    w = element.width
    h = element.width / frame_ar
    return {"x": 0, "y": (element.height - h) / 2.0, "w": w, "h": h}


def normalized_camera_to_element(
    nx: float,
    ny: float,
    frame: Size,
    element: Size,
    config: MapperConfig,
) -> dict[str, float]:
    """Map a normalized camera point onto element-local pixels."""
    dx, dy = camera_to_display_normalized(nx, ny, config.mirrored)
    vis = visible_video_rect(frame, element, config.object_fit)
    return {
        "x": vis["x"] + dx * vis["w"],
        "y": vis["y"] + dy * vis["h"],
    }


def nearest_object(
    point: dict[str, float],
    objects: list[dict],
) -> dict | None:
    """Pick the detected object whose normalized center is closest to point."""
    if not objects:
        return None
    px, py = point["x"], point["y"]
    best = None
    best_d = 1e9
    for obj in objects:
        c = obj.get("center") or bbox_center(obj.get("normalized_bbox") or obj.get("bbox") or {})
        if "x" not in c:
            continue
        d = (c["x"] - px) ** 2 + (c["y"] - py) ** 2
        if d < best_d:
            best_d = d
            best = obj
    return best
