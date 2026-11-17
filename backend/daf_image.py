"""Select DAF text detections that overlap task-relevant fields."""

import json
import os
import subprocess
import sys

from bootstrap import ROOT
from .image_marks import intersection

THRESHOLD = 0.40


def available():
    return all((ROOT / path).is_file() for path in (
        "models/daf/srnet-tensors.pt", "vendor/OSTF/configs/fasterrcnn_xsrnet.py",
        "runtime/forensics-pilot/daf-torch/torch/__init__.py",
        "runtime/forensics-pilot/daf-helpers/mmcv/__init__.py",
    ))


def relevant_detections(detections, fields, threshold=THRESHOLD):
    regions = []
    for item in sorted(detections, key=lambda item: item["peak"], reverse=True):
        if item["peak"] <= threshold:
            continue
        x1, y1, x2, y2 = item["box"]
        area = (x2 - x1) * (y2 - y1)
        if x2 <= x1 or y2 <= y1:
            continue
        for field_box, field in fields:
            overlap, clipped = intersection(item["box"], field_box)
            if overlap >= area * 0.5:
                regions.append({"box": clipped, "field": field, "peak": round(item["peak"], 5)})
                break
    return regions[:12]


def predict(path, fields, *, threshold=THRESHOLD):
    from .detector import lock

    result = {"method": "daf", "threshold": threshold, "regions": [],
              "source": {"repo": "qcf-568/OSTF", "version": "DAF Faster R-CNN / SRNet"}}
    if not fields:
        return {**result, "status": "disabled"}
    if not available():
        return {**result, "status": "unavailable", "note": "文字编辑检查暂不可用。"}
    cache = ROOT / "runtime/forensics-pilot"
    with lock:
        output = subprocess.run(
            [sys.executable, "-B", str(ROOT / "backend/daf_worker.py"), str(path)], cwd=ROOT,
            env={**os.environ, "HF_HUB_OFFLINE": "1", "PYTHONUTF8": "1", "TEMP": str(cache),
                 "TMP": str(cache), "MPLCONFIGDIR": str(cache / "mpl")},
            capture_output=True, text=True, encoding="utf-8", timeout=150,
        )
    if output.returncode:
        raise RuntimeError(output.stderr.strip()[-2500:] or "DAF worker failed")
    detections = json.loads(output.stdout.splitlines()[-1])
    return {**result, "status": "completed", "regions": relevant_detections(detections, fields, threshold)}
