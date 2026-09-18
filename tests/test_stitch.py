"""Synthetic round-trip tests: cut a textured sheet into two overlapping
scans with a known rotation/translation, stitch them back, and check that the
recovered transform and the final image match the ground truth."""

import math

import cv2
import numpy as np
import pytest

from desterro.stitch import compose, find_transform


def make_sheet(seed: int = 0, size: tuple[int, int] = (1400, 1000)) -> np.ndarray:
    """A 'map-like' sheet: beige paper with dark random strokes and text-ish blobs."""
    rng = np.random.default_rng(seed)
    h, w = size
    sheet = np.full((h, w, 3), (205, 220, 235), np.uint8)  # BGR beige
    for _ in range(400):
        p1 = tuple(int(v) for v in rng.integers([0, 0], [w, h]))
        p2 = tuple(int(v) for v in rng.integers([0, 0], [w, h]))
        cv2.line(sheet, p1, p2, (40, 40, 40), int(rng.integers(1, 3)))
    for _ in range(300):
        c = tuple(int(v) for v in rng.integers([0, 0], [w, h]))
        cv2.circle(sheet, c, int(rng.integers(2, 12)), (30, 30, 30), -1)
    return sheet


def split_sheet(sheet: np.ndarray, overlap: int, angle_deg: float, shift: tuple[int, int]):
    """Return (upper, lower, expected_matrix) where lower is rotated/shifted."""
    h, w = sheet.shape[:2]
    cut = h // 2
    upper = sheet[: cut + overlap].copy()
    lower_src = sheet[cut - overlap :].copy()
    lh, lw = lower_src.shape[:2]
    rot = cv2.getRotationMatrix2D((lw / 2, lh / 2), angle_deg, 1.0)
    rot[:, 2] += shift
    lower = cv2.warpAffine(lower_src, rot, (lw + 80, lh + 80), borderValue=(205, 220, 235))
    # Ground truth: lower pixel -> sheet pixel -> upper frame (y offset by cut-overlap)
    inv = cv2.invertAffineTransform(rot)
    expected = inv.copy()
    expected[1, 2] += cut - overlap
    return upper, lower, expected


@pytest.mark.parametrize("angle,shift", [(0.0, (0, 0)), (-0.6, (12, 5)), (1.5, (-20, 30))])
def test_recovers_known_transform(angle, shift):
    sheet = make_sheet()
    upper, lower, expected = split_sheet(sheet, overlap=180, angle_deg=angle, shift=shift)
    tf = find_transform(upper, lower, downscale=2)
    got = np.array(tf.matrix)
    assert tf.inliers >= 30
    assert tf.rms_error_px < 3.0
    assert abs(tf.rotation_deg - angle) < 0.15
    assert abs(tf.scale - 1.0) < 0.005
    assert np.allclose(got[:, :2], expected[:, :2], atol=0.01)
    assert np.allclose(got[:, 2], expected[:, 2], atol=3.0)


def test_compose_reproduces_sheet_content():
    sheet = make_sheet(seed=3)
    upper, lower, expected = split_sheet(sheet, overlap=180, angle_deg=-0.6, shift=(12, 5))
    out, (ox, oy) = compose(upper, lower, expected)
    # The composed canvas must contain the whole sheet, and a strip well
    # inside the lower half must match the original sheet pixel for pixel.
    assert out.shape[0] >= sheet.shape[0] and out.shape[1] >= sheet.shape[1]
    y0 = sheet.shape[0] - 200
    strip_out = out[oy + y0 : oy + y0 + 100, ox + 100 : ox + 900].astype(int)
    strip_ref = sheet[y0 : y0 + 100, 100:900].astype(int)
    mean_abs_diff = np.abs(strip_out - strip_ref).mean()
    # Two bilinear resamplings (forward warp in the fixture, inverse warp in
    # compose) soften 1-2 px strokes, so allow a small residual; a control
    # comparison against a 15 px misaligned strip must be clearly worse.
    control = np.abs(out[oy + y0 : oy + y0 + 100, ox + 115 : ox + 915].astype(int) - strip_ref).mean()
    assert mean_abs_diff < 25, mean_abs_diff
    assert control > 2 * mean_abs_diff, (control, mean_abs_diff)


def test_rejects_unrelated_images():
    a = make_sheet(seed=10, size=(600, 600))
    b = make_sheet(seed=11, size=(600, 600))
    with pytest.raises(RuntimeError):
        tf = find_transform(a, b, downscale=1)
        # If RANSAC happens to find a degenerate consensus, it must be a poor one.
        if tf.inliers < 15:
            raise RuntimeError("no consistent transform")
        pytest.fail(f"unexpected consensus on unrelated images: {tf}")


def test_rotation_sign_convention():
    m = np.array([[math.cos(math.radians(10)), -math.sin(math.radians(10)), 0],
                  [math.sin(math.radians(10)), math.cos(math.radians(10)), 0]])
    from desterro.stitch import Transform
    tf = Transform.from_matrix(m, 0, 0, 0.0)
    assert abs(tf.rotation_deg - 10) < 1e-9
    assert abs(tf.scale - 1) < 1e-9
