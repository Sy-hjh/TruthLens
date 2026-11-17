"""Local FUSED inspection and marked report thumbnails."""

import base64
from io import BytesIO
import json
import logging
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageOps
import numpy as np

from bootstrap import ROOT

VENDOR = ROOT / "vendor/FUSED"
WEIGHTS = ROOT / "models/fused"
CHECKPOINT = WEIGHTS / "fused_opensdi.pth"
BACKBONE = WEIGHTS / "convnext.safetensors"
METHOD = "fused"
MASK_THRESHOLD = 0.5
PHOTO_MASK_THRESHOLD = 0.75


def available():
    return (
        (VENDOR / "fused/model/model.py").is_file()
        and CHECKPOINT.is_file() and CHECKPOINT.stat().st_size == 319859039
        and BACKBONE.is_file() and BACKBONE.stat().st_size == 3386218152
    )


def marked_preview(image, regions):
    preview = ImageOps.exif_transpose(image).convert("RGB")
    preview.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
    width, height = preview.size
    canvas = ImageDraw.Draw(preview)
    stroke = max(2, round(max(width, height) * 0.004))
    for region in regions:
        x1, y1, x2, y2 = region["box"]
        bounds = (round(x1 * (width - 1)), round(y1 * (height - 1)),
                  round(x2 * (width - 1)), round(y2 * (height - 1)))
        detectors = region.get("detectors", [])
        if detectors == ["reference"]:
            color = "#2366ba"
        elif len(detectors) == 1:
            color = "#b97900"
        else:
            color = "#d81b39"
        canvas.rectangle(bounds, outline=color, width=stroke)
    encoded = BytesIO()
    preview.save(encoded, format="JPEG", quality=88, optimize=True, subsampling=0)
    return base64.b64encode(encoded.getvalue()).decode("ascii")


def photo_regions(values, threshold=PHOTO_MASK_THRESHOLD):
    """Extract concentrated FUSED responses for photos without document fields."""
    from scipy.ndimage import find_objects, label

    height, width = values.shape
    components, _ = label(values >= round(255 * threshold))
    sizes = np.bincount(components.ravel())
    minimum = max(16, round(values.size * 0.005))
    regions = []
    for index, (ys, xs) in enumerate(find_objects(components), start=1):
        pixels = int(sizes[index])
        box_area = (ys.stop - ys.start) * (xs.stop - xs.start)
        if pixels < minimum or box_area > 0.5 * values.size or pixels < 0.25 * box_area:
            continue
        peak = values[ys, xs][components[ys, xs] == index].max()
        regions.append({"box": [xs.start / width, ys.start / height, xs.stop / width, ys.stop / height],
                        "peak": round(float(peak) / 255, 4), "pixels": pixels})
    return sorted(regions, key=lambda region: region["pixels"], reverse=True)[:5]


def predict(path, image, *, context="", ocr=None, mask_threshold=MASK_THRESHOLD, photo_threshold=PHOTO_MASK_THRESHOLD):
    from .chat_ocr import NoReadableText, read
    from .detector import lock
    from .image_fields import document_kind, field_names, relevant_regions

    with lock:
        output = subprocess.run(
            [sys.executable, "-B", str(ROOT / "backend/fused_worker.py"), str(path)],
            cwd=ROOT,
            env={**os.environ, "HF_HUB_OFFLINE": "1", "PYTHONUTF8": "1"},
            capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
    if output.returncode:
        raise RuntimeError(output.stderr.strip()[-2500:] or "FUSED worker failed")
    mask = json.loads(output.stdout.splitlines()[-1])
    result = {
        "status": "completed", "method": METHOD, "mask_threshold": mask_threshold, "photo_threshold": photo_threshold,
        "regions": [], "relevance": "no_response",
        "source": {"repo": "AntonNuzhdin/FUSED", "version": "OpenSDID / e8580eb"},
    }
    oriented = ImageOps.exif_transpose(image)
    if ocr is None:
        try:
            ocr = read(oriented)
        except NoReadableText:
            ocr = {}
        except Exception:
            logging.exception("Read task fields for FUSED")
            ocr = {"status": "unavailable"}
    ocr_failed = ocr.get("status") == "unavailable"
    lines = ocr.get("lines", [])
    result["document_kind"] = document_kind(lines)
    result["document_fields"] = field_names(lines)
    if not mask:
        return result
    with Image.open(BytesIO(base64.b64decode(mask))) as mask_image:
        values = np.asarray(mask_image)
        coverage = float(np.mean(values >= round(255 * mask_threshold)))
        result["response_coverage"] = round(coverage, 4)
        if coverage >= 0.9:
            result["relevance"] = "diffuse"
            return result
        fields_regions, fields_found = relevant_regions(values, lines, oriented.size, context, threshold=mask_threshold)
        if not fields_found and not result["document_fields"] and result["document_kind"] == "image" and not ocr_failed:
            result["regions"] = photo_regions(values, photo_threshold)
            result["relevance"] = "photo_region" if result["regions"] else "no_response"
            return result
        regions = fields_regions
    result["regions"] = regions
    result["relevance"] = ("matched" if regions else "unavailable" if ocr_failed else
                           "irrelevant" if fields_found else "unmatched")
    return result
