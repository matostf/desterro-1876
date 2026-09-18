"""Stitch two overlapping flatbed scans of a single sheet into one image.

The 1876 *Planta topographica da Cidade do Desterro* is larger than the
scanner bed, so the UFSC library digitised it as two overlapping A4 scans
(upper half and lower half).  This module recovers the geometric relation
between the two scans from image content alone, warps the lower scan into
the frame of the upper one and blends the overlap.

Pipeline
--------
1. Detect SIFT keypoints on down-sampled greyscale copies of both scans.
2. Match descriptors (FLANN, k=2) and keep matches that pass Lowe's ratio
   test.
3. Estimate a *partial affine* transform (rotation + uniform scale +
   translation) with RANSAC.  A flatbed scan of a flat sheet cannot
   introduce perspective, so a 4-degree-of-freedom model is both sufficient
   and far more robust than a full homography.
4. Rescale the transform to full resolution, warp the lower scan into the
   upper scan's coordinate system and blend along a narrow seam placed on
   the line equidistant from both scan borders.

Every run writes a JSON report (matches, inliers, RMS reprojection error,
recovered rotation/scale/translation) so the result can be audited.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class Transform:
    """Partial-affine transform (2x3) mapping *moving* pixels into *fixed*."""

    matrix: list[list[float]]
    rotation_deg: float
    scale: float
    tx: float
    ty: float
    matches: int
    inliers: int
    rms_error_px: float

    @classmethod
    def from_matrix(
        cls, m: np.ndarray, matches: int, inliers: int, rms: float
    ) -> "Transform":
        a, b = float(m[0, 0]), float(m[0, 1])
        return cls(
            matrix=m.tolist(),
            rotation_deg=math.degrees(math.atan2(-b, a)),
            scale=math.hypot(a, b),
            tx=float(m[0, 2]),
            ty=float(m[1, 2]),
            matches=matches,
            inliers=inliers,
            rms_error_px=rms,
        )


def _grey_small(img: np.ndarray, factor: int) -> np.ndarray:
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    if factor == 1:
        return grey
    return cv2.resize(grey, None, fx=1 / factor, fy=1 / factor, interpolation=cv2.INTER_AREA)


def find_transform(
    fixed: np.ndarray,
    moving: np.ndarray,
    *,
    downscale: int = 4,
    ratio: float = 0.75,
    ransac_px: float = 3.0,
    max_features: int = 20000,
) -> Transform:
    """Estimate the transform that maps *moving* onto *fixed*.

    Feature detection runs on images down-sampled by ``downscale`` (memory and
    speed); the resulting matrix is rescaled to full-resolution pixels.
    """
    sift = cv2.SIFT_create(nfeatures=max_features)
    f_small, m_small = _grey_small(fixed, downscale), _grey_small(moving, downscale)
    kp_f, des_f = sift.detectAndCompute(f_small, None)
    kp_m, des_m = sift.detectAndCompute(m_small, None)
    if des_f is None or des_m is None:
        raise RuntimeError("no SIFT descriptors found in one of the images")

    flann = cv2.FlannBasedMatcher({"algorithm": 1, "trees": 5}, {"checks": 64})
    good = [
        m
        for m, n in flann.knnMatch(des_m, des_f, k=2)
        if m.distance < ratio * n.distance
    ]
    if len(good) < 4:
        raise RuntimeError(f"only {len(good)} good matches; cannot estimate transform")

    src = np.float32([kp_m[m.queryIdx].pt for m in good])
    dst = np.float32([kp_f[m.trainIdx].pt for m in good])
    m_small_tf, inlier_mask = cv2.estimateAffinePartial2D(
        src, dst, method=cv2.RANSAC, ransacReprojThreshold=ransac_px, maxIters=5000, confidence=0.999
    )
    if m_small_tf is None:
        raise RuntimeError("RANSAC failed to find a consistent transform")

    inl = inlier_mask.ravel().astype(bool)
    proj = (m_small_tf[:, :2] @ src[inl].T).T + m_small_tf[:, 2]
    rms_small = float(np.sqrt(np.mean(np.sum((proj - dst[inl]) ** 2, axis=1))))

    # Rescale: x_full = s * x_small  =>  M_full = S M_small S^-1  (only translation scales)
    m_full = m_small_tf.copy()
    m_full[:, 2] *= downscale
    return Transform.from_matrix(m_full, len(good), int(inl.sum()), rms_small * downscale)


def compose(
    fixed: np.ndarray, moving: np.ndarray, matrix: np.ndarray, *, feather_px: float = 80.0
) -> tuple[np.ndarray, tuple[int, int]]:
    """Warp *moving* by *matrix* into *fixed*'s frame and blend both.

    Returns the composed canvas and the ``(x, y)`` position of *fixed*'s
    origin inside it (the canvas grows when the warped scan sticks out).

    The seam runs along the line equidistant from the two scan borders, with
    a linear transition ``feather_px`` wide.  A narrow seam matters: a folded
    paper sheet is not perfectly rigid, so a global similarity transform
    leaves a few pixels of residual error.  Blending the whole overlap would
    show every line twice (ghosting); a narrow seam hides the residual.
    """
    h_f, w_f = fixed.shape[:2]
    h_m, w_m = moving.shape[:2]
    corners = np.float32([[0, 0], [w_m, 0], [w_m, h_m], [0, h_m]])
    warped_corners = (matrix[:, :2] @ corners.T).T + matrix[:, 2]
    all_corners = np.vstack([warped_corners, [[0, 0], [w_f, 0], [w_f, h_f], [0, h_f]]])
    x0, y0 = np.floor(all_corners.min(axis=0)).astype(int)
    x1, y1 = np.ceil(all_corners.max(axis=0)).astype(int)
    offset = np.array([[1, 0, -x0], [0, 1, -y0]], dtype=np.float64)
    size = (int(x1 - x0), int(y1 - y0))

    m_fixed = offset.astype(np.float32)
    m_moving = np.vstack([matrix, [0, 0, 1]])
    m_moving = (np.vstack([offset, [0, 0, 1]]) @ m_moving)[:2].astype(np.float32)

    warp_f = cv2.warpAffine(fixed, m_fixed, size, flags=cv2.INTER_LINEAR)
    warp_m = cv2.warpAffine(moving, m_moving, size, flags=cv2.INTER_LINEAR)
    mask_f = cv2.warpAffine(np.full((h_f, w_f), 255, np.uint8), m_fixed, size)
    mask_m = cv2.warpAffine(np.full((h_m, w_m), 255, np.uint8), m_moving, size)

    d_f = cv2.distanceTransform(mask_f, cv2.DIST_L2, 5)
    d_m = cv2.distanceTransform(mask_m, cv2.DIST_L2, 5)
    w_fixed = np.clip((d_f - d_m) / feather_px + 0.5, 0.0, 1.0)
    w_fixed[mask_m == 0] = 1.0
    w_fixed[mask_f == 0] = 0.0
    w_fixed = w_fixed[..., None]
    out = warp_f.astype(np.float32) * w_fixed + warp_m.astype(np.float32) * (1 - w_fixed)
    return np.clip(out, 0, 255).astype(np.uint8), (int(-x0), int(-y0))


def stitch(
    upper_path: Path, lower_path: Path, out_path: Path, report_path: Path | None = None, **kw
) -> Transform:
    upper = cv2.imread(str(upper_path), cv2.IMREAD_COLOR)
    lower = cv2.imread(str(lower_path), cv2.IMREAD_COLOR)
    if upper is None or lower is None:
        raise FileNotFoundError("could not read one of the input scans")
    tf = find_transform(upper, lower, **kw)
    result, origin = compose(upper, lower, np.array(tf.matrix))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), result, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if report_path:
        report = {
            "upper": str(upper_path),
            "lower": str(lower_path),
            "output": str(out_path),
            "output_size_px": [int(result.shape[1]), int(result.shape[0])],
            "upper_origin_in_output_px": list(origin),
            "transform": asdict(tf),
        }
        report_path.write_text(json.dumps(report, indent=2))
    return tf


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("upper", type=Path, help="scan of the upper half (fixed frame)")
    p.add_argument("lower", type=Path, help="scan of the lower half (warped onto the upper)")
    p.add_argument("-o", "--out", type=Path, default=Path("output/stitched.jpg"))
    p.add_argument("--report", type=Path, default=Path("output/stitch-report.json"))
    p.add_argument("--downscale", type=int, default=4, help="feature detection scale factor")
    a = p.parse_args(argv)
    tf = stitch(a.upper, a.lower, a.out, a.report, downscale=a.downscale)
    print(
        f"matches={tf.matches} inliers={tf.inliers} rms={tf.rms_error_px:.2f}px "
        f"rot={tf.rotation_deg:+.3f}deg scale={tf.scale:.5f} t=({tf.tx:.1f},{tf.ty:.1f})"
    )
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
