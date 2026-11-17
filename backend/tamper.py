"""Adapter for original TruFor inference, retaining its preprocessing and strict state loading."""

import base64, io, json, sys
import numpy as np
import torch
from PIL import Image, ImageOps
from scipy.ndimage import find_objects, label
from bootstrap import ROOT
from .detector import lock

ALERT_THRESHOLD = 0.95
REGION_THRESHOLD = 0.75
MAX_REGIONS = 5


def anomaly_regions(heat):
    values = np.asarray(heat.convert("L"), dtype=np.float32) / 255
    height, width = values.shape
    components, count = label(values >= REGION_THRESHOLD, structure=np.ones((3, 3)))
    if not count:
        return []
    sizes = np.bincount(components.ravel())
    minimum = max(9, int(width * height * 0.00006))
    candidates = []
    for index, (ys, xs) in enumerate(find_objects(components), start=1):
        if sizes[index] < minimum:
            continue
        peak = float(values[ys, xs][components[ys, xs] == index].max())
        if peak >= 0.8:
            candidates.append((sizes[index], {
                "box": [xs.start / width, ys.start / height, xs.stop / width, ys.stop / height],
                "peak": round(peak, 3),
            }))
    candidates.sort(key=lambda candidate: candidate[0], reverse=True)
    return [region for _, region in candidates[:MAX_REGIONS]]


def with_saved_regions(report):
    """Read legacy evidence from the saved model map without rewriting reports."""
    modules = report.get("modules", {})
    result = modules.get("tamper", {})
    if result.get("status") != "completed" or "regions" in result:
        return report
    data = result.get("map_png", "")
    if not isinstance(data, str) or not data.startswith("data:image/png;base64,"):
        return report
    try:
        with Image.open(io.BytesIO(base64.b64decode(data.split(",", 1)[1], validate=True))) as heat:
            regions = anomaly_regions(heat)
    except (ValueError, OSError):
        return report
    return {**report, "modules": {**modules, "tamper": {**result, "regions": regions}},
            "summary": "发现局部异常区域，请核对原图" if regions else report["summary"]}

def _checkpoint_scalar(dtype, data):
    return np.core.multiarray.scalar(dtype, data)

# Author checkpoint uses the NumPy 1.x pickle name. Torch 2.5 resolves allowlist
# entries by module and name, so register this exact legacy scalar constructor.
_checkpoint_scalar.__module__ = "numpy.core.multiarray"
_checkpoint_scalar.__name__ = "scalar"


def available():
    return (ROOT / "models/tamper/trufor.pth.tar").exists() and (
        ROOT / "models/tamper/source.json"
    ).exists()


def predict(image):
    if not available():
        raise RuntimeError("局部篡改模型尚未安装")
    with lock:
        source = ROOT / "vendor/TruFor/TruFor_train_test"
        sys.path.insert(0, str(source))
        from lib.config import config
        from lib.models.cmx.builder_np_conf import EncoderDecoder

        cfg = config.clone()
        cfg.defrost()
        cfg.merge_from_file(str(source / "lib/config/trufor_ph3.yaml"))
        cfg.freeze()
        model = EncoderDecoder(cfg=cfg)
        safe = [
            _checkpoint_scalar,
            np.dtype,
            type(np.dtype("float64")),
            type(np.dtype("float32")),
        ]
        with torch.serialization.safe_globals(safe):
            checkpoint = torch.load(
                ROOT / "models/tamper/trufor.pth.tar",
                map_location="cpu",
                weights_only=True,
            )
        model.load_state_dict(checkpoint["state_dict"], strict=True)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device).eval()
        image = ImageOps.exif_transpose(image)
        original = image.size
        image.thumbnail((1024, 1024))
        x = (
            torch.from_numpy(np.asarray(image.convert("RGB")).copy().transpose(2, 0, 1))
            .float()
            .unsqueeze(0)
            .to(device)
            / 256.0
        )
        with torch.inference_mode():
            pred, conf, det, _ = model(x, save_np=False)
            score = float(torch.sigmoid(det).cpu().item())
            anomaly = pred.softmax(1)[0, 1].cpu().numpy()
            reliability = float(torch.sigmoid(conf).mean().cpu())
        # This is a visualization of the model's actual anomaly matrix, not an edited photograph.
        heat = Image.fromarray(np.uint8(np.clip(anomaly, 0, 1) * 255), "L")
        heat.thumbnail((512, 512))
        buffer = io.BytesIO()
        heat.save(buffer, format="PNG")
        result = {
            "status": "completed",
            "score": score,
            "threshold": ALERT_THRESHOLD,
            "map_png": "data:image/png;base64,"
            + base64.b64encode(buffer.getvalue()).decode(),
            "map_size": list(heat.size),
            "regions": anomaly_regions(heat),
            "processed_size": list(image.size),
            "original_size": list(original),
            "reliability_mean": reliability,
            "source": json.loads((ROOT / "models/tamper/source.json").read_text()),
            "note": "检测图片中的编辑异常，作为 AI 内容核验的风险线索。普通修图、截图、压缩和缩放也可能影响分数。",
        }
        del model, checkpoint, x
        if device == "cuda":
            torch.cuda.empty_cache()
        return result
