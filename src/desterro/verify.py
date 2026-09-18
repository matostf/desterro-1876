"""Verify a stitched map against an independent digitisation of the same sheet.

The UFSC library holds one physical copy of the 1876 *Planta topographica*;
the Biblioteca Nacional (Rio de Janeiro) holds another and published its own
single-image scan.  If the stitch is geometrically correct, the stitched
image and the Biblioteca Nacional scan must be related by a single
similarity transform (rotation + uniform scale + translation) across the
*whole* sheet, including the overlap zone.  A stitching error would show up
as a poor RANSAC consensus (few inliers) or a large reprojection error.

This module reuses the same feature pipeline as ``stitch.py`` and writes a
JSON report with the recovered transform and residuals.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import cv2

from .stitch import find_transform


def verify(stitched_path: Path, reference_path: Path, report_path: Path | None = None, **kw):
    stitched = cv2.imread(str(stitched_path), cv2.IMREAD_COLOR)
    reference = cv2.imread(str(reference_path), cv2.IMREAD_COLOR)
    if stitched is None or reference is None:
        raise FileNotFoundError("could not read stitched image or reference scan")
    tf = find_transform(reference, stitched, **kw)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "stitched": str(stitched_path),
                    "reference": str(reference_path),
                    "stitched_to_reference": asdict(tf),
                },
                indent=2,
            )
        )
    return tf


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("stitched", type=Path)
    p.add_argument("reference", type=Path)
    p.add_argument("--report", type=Path, default=Path("output/verify-report.json"))
    p.add_argument("--downscale", type=int, default=4)
    a = p.parse_args(argv)
    tf = verify(a.stitched, a.reference, a.report, downscale=a.downscale)
    print(
        f"stitched -> reference: matches={tf.matches} inliers={tf.inliers} "
        f"rms={tf.rms_error_px:.2f}px rot={tf.rotation_deg:+.3f}deg scale={tf.scale:.4f}"
    )


if __name__ == "__main__":
    main()
