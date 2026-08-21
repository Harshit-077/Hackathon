"""
Map camera-space boxes to display / viewport space.

Coordinates are always normalized 0–1 relative to the source frame.
Never assumes a fixed webcam resolution.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Viewport:
    width: float
    height: float


@dataclass(frozen=True)
class FrameSize:
    width: float
    height: float


@dataclass(frozen=True)
class DisplayBox:
    x: float
    y: float
    w: float
    h: float


class VisionCoordinateMapper:
    """Handles letterboxing, object-fit, mirroring, and device pixel ratio."""

    def __init__(
        self,
        frame: FrameSize,
        viewport: Viewport,
        object_fit: str = "cover",
        mirrored: bool = True,
        device_pixel_ratio: float = 1.0,
    ) -> None:
        if frame.width <= 0 or frame.height <= 0:
            raise ValueError("frame dimensions must be positive")
        if viewport.width <= 0 or viewport.height <= 0:
            raise ValueError("viewport dimensions must be positive")
        if device_pixel_ratio <= 0:
            raise ValueError("device_pixel_ratio must be positive")
        self.frame = frame
        self.viewport = viewport
        self.object_fit = object_fit
        self.mirrored = mirrored
        self.device_pixel_ratio = device_pixel_ratio

    def camera_to_normalized(self, x: float, y: float) -> tuple[float, float]:
        nx = x / self.frame.width
        ny = y / self.frame.height
        return self._clamp01(nx), self._clamp01(ny)

    def apply_mirror(self, nx: float, ny: float) -> tuple[float, float]:
        if self.mirrored:
            nx = 1.0 - nx
        return nx, ny  # never mirror Y

    def visible_source_rect(self) -> tuple[float, float, float, float]:
        """
        Normalized source rect (sx, sy, sw, sh) shown in the viewport
        after object-fit cropping / letterboxing.
        """
        frame_ar = self.frame.width / self.frame.height
        view_ar = self.viewport.width / self.viewport.height

        if self.object_fit == "contain":
            if frame_ar > view_ar:
                # letterbox top/bottom: full width visible
                return 0.0, 0.0, 1.0, 1.0
            return 0.0, 0.0, 1.0, 1.0

        # cover: crop overflow
        if frame_ar > view_ar:
            visible_w = view_ar / frame_ar
            sx = (1.0 - visible_w) / 2.0
            return sx, 0.0, visible_w, 1.0
        visible_h = frame_ar / view_ar
        sy = (1.0 - visible_h) / 2.0
        return 0.0, sy, 1.0, visible_h

    def contain_letterbox(self) -> tuple[float, float, float, float]:
        """Viewport-normalized dest rect (dx, dy, dw, dh) for object-fit: contain."""
        frame_ar = self.frame.width / self.frame.height
        view_ar = self.viewport.width / self.viewport.height
        if frame_ar > view_ar:
            dw, dh = 1.0, view_ar / frame_ar
            return 0.0, (1.0 - dh) / 2.0, dw, dh
        dw, dh = frame_ar / view_ar, 1.0
        return (1.0 - dw) / 2.0, 0.0, dw, dh

    def normalized_box_to_viewport(
        self,
        nx: float,
        ny: float,
        nw: float,
        nh: float,
    ) -> DisplayBox:
        """Map a camera-normalized box to viewport-normalized display coords."""
        cx, cy = self.apply_mirror(nx + nw / 2.0, ny + nh / 2.0)
        left = cx - nw / 2.0
        top = cy - nh / 2.0

        if self.object_fit == "contain":
            dx, dy, dw, dh = self.contain_letterbox()
            return DisplayBox(
                x=dx + left * dw,
                y=dy + top * dh,
                w=nw * dw,
                h=nh * dh,
            )

        sx, sy, sw, sh = self.visible_source_rect()
        # cover: source crop mapped onto full viewport
        rel_x = (left - sx) / sw if sw else 0.0
        rel_y = (top - sy) / sh if sh else 0.0
        return DisplayBox(x=rel_x, y=rel_y, w=nw / sw if sw else 0.0, h=nh / sh if sh else 0.0)

    def viewport_px(self, box: DisplayBox) -> dict[str, float]:
        dpr = self.device_pixel_ratio
        return {
            "x": box.x * self.viewport.width * dpr / dpr,
            "y": box.y * self.viewport.height,
            "w": box.w * self.viewport.width,
            "h": box.h * self.viewport.height,
        }

    @staticmethod
    def _clamp01(v: float) -> float:
        return max(0.0, min(1.0, v))
