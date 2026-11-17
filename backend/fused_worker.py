"""Run FUSED independently of the other local detectors."""

import base64
from io import BytesIO
import inspect
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.fused_image import BACKBONE, CHECKPOINT, MASK_THRESHOLD, VENDOR

import numpy as np
from PIL import Image, ImageOps
from scipy.ndimage import label
import timm
import torch
from torchvision import transforms

sys.path.insert(0, str(VENDOR))

from fused.model.model import FUSED


def load_model(device):
    checkpoint = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
    config = checkpoint["cfg"]["model"]
    parameters = inspect.signature(FUSED.__init__).parameters
    create_model = timm.create_model

    def load_backbone(name, **kwargs):
        if name != "convnext_xxlarge.clip_laion2b_soup":
            raise ValueError(f"Unexpected FUSED backbone: {name}")
        return create_model(name, pretrained_cfg_overlay={"file": str(BACKBONE)}, **kwargs)

    with patch.object(timm, "create_model", load_backbone):
        model = FUSED(**{key: value for key, value in config.items() if key in parameters})
    state = {key.removeprefix("module."): value for key, value in checkpoint["state_dict"].items()}
    loaded = model.load_state_dict(state, strict=False)
    missing = [key for key in loaded.missing_keys
               if not key.startswith("convnext.") and not key.endswith("num_batches_tracked")]
    legacy = {"dinov2_mean", "dinov2_std", "seg_bridge.weight", "seg_bridge.bias"}
    if missing or set(loaded.unexpected_keys) - legacy:
        raise ValueError(f"FUSED checkpoint mismatch: {loaded}")
    return model.to(device).eval()


def filtered_mask(mask):
    components, count = label(mask >= MASK_THRESHOLD)
    if not count:
        return None
    sizes = np.bincount(components.ravel())
    keep = sizes >= max(9, round(mask.size * 0.0002))
    keep[0] = False
    if not keep.any():
        return None
    encoded = BytesIO()
    Image.fromarray(np.rint(np.where(keep[components], mask, 0) * 255).astype("uint8")).save(encoded, format="PNG")
    return base64.b64encode(encoded.getvalue()).decode("ascii")


if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        torch.set_num_threads(4)
    model = load_model(device)
    preprocess = transforms.Compose([
        transforms.Resize((512, 512)), transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
    ])
    with Image.open(sys.argv[1]) as source:
        batch = preprocess(ImageOps.exif_transpose(source).convert("RGB")).unsqueeze(0).to(device)
    with torch.inference_mode(), torch.autocast("cuda", enabled=device.type == "cuda"):
        mask = model(batch)["logits"].sigmoid()[0, 0].float().cpu().numpy()
    if not np.isfinite(mask).all():
        raise ValueError("FUSED produced a non-finite mask")
    print(json.dumps(filtered_mask(mask)))
