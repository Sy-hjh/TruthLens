"""Generate report marks for corroborated and individual detector findings."""

from .fraud_risk import score_alert

MARK_POLICY = "image-marks-v4"
DAF_YELLOW_POLICIES = {MARK_POLICY, "fused-daf-colors-v3"}
FUSED_YELLOW_POLICIES = {*DAF_YELLOW_POLICIES, "fused-daf-colors-v2"}
SUPPORTED_MARK_POLICIES = {*FUSED_YELLOW_POLICIES, "fused-daf-overlap-v1"}
DAF_REVIEW_THRESHOLD = 0.50


def intersection(a, b):
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    return max(0, right - left) * max(0, bottom - top), [left, top, right, bottom]


def _overlaps(a, b):
    area, _ = intersection(a, b)
    smaller = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return smaller > 0 and area >= 0.2 * smaller


def combined_regions(modules):
    fused, daf = modules.get("tamper", {}), modules.get("daf", {})
    if fused.get("method") != "fused" or fused.get("status") != "completed" or daf.get("status") != "completed":
        return []
    confirmed = []
    for local in fused.get("regions", []):
        field = local.get("field")
        if not field or local.get("peak", 0) < fused.get("mask_threshold", 0.5):
            continue
        for text in sorted(daf.get("regions", []), key=lambda item: item.get("peak", 0), reverse=True):
            if text.get("field") != field or text.get("peak", 0) <= daf.get("threshold", 0.4):
                continue
            if not _overlaps(local["box"], text["box"]):
                continue
            _, box = intersection(local["box"], text["box"])
            if not any(item["field"] == field and _overlaps(item["box"], box) for item in confirmed):
                confirmed.append({"box": box, "field": field, "detectors": ["tamper", "daf"]})
    return confirmed


def daf_review_regions(modules):
    daf = modules.get("daf", {})
    if daf.get("status") != "completed":
        return []
    image = modules.get("image", {})
    candidates = daf.get("regions", [])
    focus_fields = set(daf.get("focus_fields", []))
    all_fields = modules.get("tamper", {}).get("document_fields", [])
    hit_fields = {item["field"] for item in candidates if item.get("field")}
    diffuse = len(hit_fields) >= 3 and len(hit_fields) >= 0.6 * len(all_fields)
    has_image_support = not diffuse and (image.get("generation_label") or score_alert(image))
    selected = []
    for item in candidates:
        field = item.get("field")
        if not field or item.get("peak", 0) < daf.get("review_threshold", DAF_REVIEW_THRESHOLD) or not (field in focus_fields or has_image_support):
            continue
        if not any(region["field"] == field and _overlaps(region["box"], item["box"]) for region in selected):
            selected.append({"field": field, "box": item["box"], "detectors": ["daf"]})
    return selected


def _fused_review_regions(modules):
    fused = modules.get("tamper", {})
    if (fused.get("method") != "fused" or fused.get("status") != "completed"
            or fused.get("relevance") not in {"matched", "photo_region"}):
        return []

    single = []
    threshold = (round(255 * fused["photo_threshold"]) / 255
                 if fused["relevance"] == "photo_region" and "photo_threshold" in fused
                 else fused.get("mask_threshold", 0.5))
    for candidate in fused.get("regions", []):
        if candidate.get("peak", 0) + 0.00005 < threshold:
            continue
        field = candidate.get("field")
        if not field and fused["relevance"] != "photo_region":
            continue
        single.append({"field": field, "box": candidate["box"], "detectors": ["tamper"]})
    return single


def report_regions(modules):
    confirmed = combined_regions(modules)
    candidates = _fused_review_regions(modules) + daf_review_regions(modules)
    single = [item for item in candidates if not any(
        region["field"] == item["field"] and _overlaps(item["box"], region["box"]) for region in confirmed
    )]
    model_marks = single + confirmed
    reference = modules.get("reference", {})
    if reference.get("status") != "completed":
        return model_marks
    differences = [
        {**item, "detectors": ["reference"]}
        for item in reference.get("regions", []) if not any(
            mark["field"] == item["field"] and _overlaps(mark["box"], item["box"]) for mark in model_marks
        )
    ]
    return differences + model_marks
