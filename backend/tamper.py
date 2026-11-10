"""Adapter for original TruFor inference, retaining its preprocessing and strict state loading."""

import base64, io, json, sys
import numpy as np
import torch
from PIL import Image
from bootstrap import ROOT
from .detector import lock


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
            (np._core.multiarray.scalar, "numpy.core.multiarray.scalar"),
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
        original = image.size
        image = image.copy()
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
            "map_png": "data:image/png;base64,"
            + base64.b64encode(buffer.getvalue()).decode(),
            "map_size": list(heat.size),
            "processed_size": list(image.size),
            "original_size": list(original),
            "reliability_mean": reliability,
            "source": json.loads((ROOT / "models/tamper/source.json").read_text()),
            "note": "亮处表示模型预测的异常区域，不等于已证实修改；压缩、截图、缩放可能影响结果。",
        }
        del model, checkpoint, x
        if device == "cuda":
            torch.cuda.empty_cache()
        return result
