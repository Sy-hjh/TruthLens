"""Align a user-supplied reference and locate differences in key fields."""

import cv2
import numpy as np

from .image_fields import task_fields


def compare_fields(image, reference, reference_lines, context):
    width, height = image.size
    ref_width, ref_height = reference.size
    fields = task_fields(reference_lines, reference.size, context)
    if not fields or abs(width * ref_height / (height * ref_width) - 1) > 0.05:
        return {"status": "unavailable", "regions": [], "note": "参考图与待查图片需为可对齐的同版材料。"}
    scale = min(1, 1600 / max(width, height))
    size = (round(width * scale), round(height * scale))

    def grayscale(source):
        pixels = np.asarray(source.convert("L"))
        return cv2.GaussianBlur(cv2.resize(pixels, size, interpolation=cv2.INTER_AREA), (3, 3), 0)

    current, original = grayscale(image), grayscale(reference)
    size_x, size_y = size
    mask = np.full(current.shape, 255, dtype=np.uint8)
    for (left, top, right, bottom), _ in fields:
        mask[int(top * size_y):round(bottom * size_y), int(left * size_x):round(right * size_x)] = 0
    try:
        correlation, transform = cv2.findTransformECC(
            original, current, np.eye(2, 3, dtype=np.float32), cv2.MOTION_AFFINE,
            (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 45, 1e-5), mask, 5,
        )
    except cv2.error:
        return {"status": "unavailable", "regions": [], "note": "参考图未能与待查图片可靠对齐。"}
    if correlation < 0.87 or np.max(np.abs(transform[:, :2] - np.eye(2))) > 0.06 or np.max(np.abs(transform[:, 2])) > 0.04 * min(size):
        return {"status": "unavailable", "regions": [], "note": "参考图未能与待查图片可靠对齐。"}

    aligned = cv2.warpAffine(current, transform, size, flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    kernel = np.ones((3, 3), dtype=np.uint8)
    changes = ((cv2.erode(aligned, kernel).astype(np.int16) - cv2.dilate(original, kernel) > 32)
               | (cv2.erode(original, kernel).astype(np.int16) - cv2.dilate(aligned, kernel) > 32))
    regions = []
    for (left, top, right, bottom), field in fields:
        x1, y1, x2, y2 = round(left * size_x), round(top * size_y), round(right * size_x), round(bottom * size_y)
        crop = changes[y1:y2, x1:x2]
        if not crop.size or crop.sum() < max(24, 0.012 * crop.size):
            continue
        grouped = cv2.dilate(crop.astype(np.uint8), np.ones((3, 9), dtype=np.uint8))
        count, groups, stats, _ = cv2.connectedComponentsWithStats(grouped)
        keep = np.zeros(count, dtype=bool)
        for index in range(1, count):
            keep[index] = stats[index, cv2.CC_STAT_AREA] >= 28
        ys, xs = np.nonzero(crop & keep[groups])
        if len(xs) < max(24, 0.012 * crop.size):
            continue
        corners = np.float32([[[x1 + xs.min(), y1 + ys.min()], [x1 + xs.max() + 1, y1 + ys.max() + 1]]])
        (bx1, by1), (bx2, by2) = cv2.transform(corners, transform)[0]
        box = np.clip([(bx1 - 3) / size_x, (by1 - 3) / size_y, (bx2 + 3) / size_x, (by2 + 3) / size_y], 0, 1).tolist()
        regions.append({"field": field, "box": box})
    return {"status": "completed", "regions": regions}
