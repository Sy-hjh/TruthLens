"""Run OSTF DAF in its verified, isolated PyTorch/MMCV environment."""

import json
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    runtime = root / "runtime/forensics-pilot"
    source = root / "vendor/OSTF"
    sys.path[:0] = [str(runtime / "daf-torch"), str(runtime / "daf-helpers"), str(source)]

    import numpy as np
    from PIL import Image, ImageOps
    import torch
    from mmcv.transforms import Compose
    from mmengine.config import Config
    from mmdet.registry import MODELS
    from mmdet.structures import DetDataSample
    from mmdet.utils import register_all_modules

    torch.set_num_threads(4)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    config = Config.fromfile(source / "configs/fasterrcnn_xsrnet.py")
    config.model.test_cfg.rcnn.max_per_img = 1000
    register_all_modules()
    model = MODELS.build(config.model)
    state = torch.load(root / "models/daf/srnet-tensors.pt", map_location="cpu", weights_only=True)
    model.load_state_dict({key.removeprefix("module."): value for key, value in state.items()}, strict=True)
    del state
    model.to(device).eval()
    pipeline = Compose([dict(type="LoadImageFromNDArray"), config.test_pipeline[1]])

    with Image.open(sys.argv[1]) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
    data = pipeline({"img": np.asarray(image)[:, :, ::-1].copy(), "img_id": 0})
    tensor = torch.from_numpy(np.ascontiguousarray(data["img"].transpose(2, 0, 1)))
    sample = DetDataSample(metainfo={key: data[key] for key in ("img_id", "ori_shape", "img_shape", "scale_factor")})
    with torch.inference_mode():
        boxes, scores = model.test_step({"inputs": [tensor], "data_samples": [sample]})[0]
    width, height = image.size
    print(json.dumps([
        {"box": [box[0] / width, box[1] / height, box[2] / width, box[3] / height], "peak": score}
        for box, score in zip(boxes.cpu().tolist(), scores[:, 1].cpu().tolist())
    ], allow_nan=False))


if __name__ == "__main__":
    main()
