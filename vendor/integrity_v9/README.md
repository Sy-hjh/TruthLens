---
license: apache-2.0
library_name: pytorch
pipeline_tag: image-segmentation
base_model: timm/convnext_tiny.fb_in22k
datasets:
  - shawnmichael/CarDD
tags:
  - car-damage
  - auto-damage
  - image-forensics
  - inpainting-detection
  - ai-edit-detection
  - manipulation-localization
  - photo-integrity
  - convnext
---

# Car Damage Photo Integrity Detector v9

Detects and localizes AI edits in **car / auto damage photos**, meaning regions that were inpainted to add, remove, or exaggerate vehicle damage. For each photo it returns a per-pixel **tamper heatmap** and an **image score** (higher = more likely edited).

**Author:** Sai Charan Obuladinne ([obuladinnesai](https://huggingface.co/obuladinnesai)) · **Released:** Oct 6, 2026 · **License:** Apache-2.0

Earlier versions (v5–v8, with their code and reports) are in [obuladinnesai/claim-photo-integrity-detector-v5](https://huggingface.co/obuladinnesai/claim-photo-integrity-detector-v5). This repo holds the same v9 weights as that repo's `v9/` folder, as a standalone model page.

## Results

All numbers are at a **2% false-positive rate on real photos**. The threshold is set so that only 12 of the 600 real car-damage test photos (CarDD val/test) are flagged (threshold = 12th-highest of the 600 real scores), so about **2 of every 100 genuine photos** get wrongly flagged. The percentage is the **share of edited photos caught** at that threshold. The threshold is set separately for each photo condition.

| Model | Photo condition | Edited photos caught @ 2% FPR | AUROC |
|---|---|---|---|
| **v9** | Re-saved as JPEG quality 90 | **85.3%** | 0.948 |
| **v9** | Upload setting (max side 1600 px + JPEG quality 85) | **81.6%** | 0.933 |
| v7 (previous best) | Original files | 56.0% | 0.888 |
| v7 | Upload setting | 52.9% | 0.870 |

In the upload setting, v9 flags about 82 of every 100 edited photos while wrongly flagging about 2 of every 100 real ones.

Full report: [`reports/report_v7_vs_v9.html`](reports/report_v7_vs_v9.html) (download it and open it in a browser).

### Limitations

- Not yet at the 90% target.
- Small edits (0.5–3% of the photo) are the weak spot: 61.3% caught in the upload setting, 67.8% after JPEG q90.
- Fully AI-generated scenes (text-to-image, not edits): only 41% (upload) / 45% (JPEG q90), while v7 catches 98–99% of those. v9 is built for localized edits.
- It is a triage signal for human review, not proof of editing or fraud.

## Model

- **Encoder:** ConvNeXt-Tiny (timm `convnext_tiny.fb_in22k`, ImageNet-22k init).
- **Noise-residual stream:** fixed SRM high-pass filters plus learned 5×5 filters, with conv stages at strides 2–16.
- **Decoder:** FPN/U-Net that fuses both streams and outputs a 1-channel tamper logit map at half resolution (stride 2).
- **Image score:** mean of the top-256 map logits (the most suspicious ~1,000 pixels).
- **Size:** ~29.4M parameters (118 MB safetensors, fp32).
- Runs at full resolution in one pass (no resizing or tiling).

## Training

- **Edited photos:** 3,298 inpaints of CarDD-train photos: Stable Diffusion 1.5 (1,474), SDXL (564), Kandinsky 2.2 (466) and LaMa (589). Pixel masks come from the difference between each inpaint and its original photo. Synthetic tiny paste-back edits make up about 20% of each batch.
- **Real photos:** CarDD train (2,607), Open Images (3,000) and private photos (1,500, not released).
- Near-duplicate leak check against the eval set.
- **Loss:** per-pixel BCE + Dice on the map, plus an image-level loss on the top-256 score.
- **Schedule:** 20k steps, batch 8, 512 px full-resolution crops, JPEG / resize / blur augmentation on real and edited photos alike. The released checkpoint is from step 16,000 (best on a held-out validation split).

## Usage

```bash
pip install torch timm safetensors pillow numpy huggingface_hub
hf download obuladinnesai/car-damage-photo-integrity-v9 --local-dir car-damage-v9   # or: huggingface-cli download ...
cd car-damage-v9
python inference.py photo.jpg                                        # default condition: jpeg_q90
python inference.py photo.jpg --condition upload --heatmap heat.png  # also saves the tamper heatmap
```

Each image prints one JSON line: `image`, `score`, `threshold`, `flagged`, `condition`, `max_heat`. `inference.py` uses `model.safetensors` / `config.json` from its own folder, or downloads them from this repo if they are missing.

```python
from inference import load_model, score_image   # run from the repo folder
net, cfg, dev = load_model()                     # local weights, else downloads from the Hub
r = score_image(net, cfg, dev, "photo.jpg", condition="upload")
print(r["score"], r["threshold"], r["flagged"])
heat = r["heatmap"]                              # H x W array in [0, 1]
```

`condition` picks the preprocessing and the matching 2%-FPR threshold from `config.json`:
- `jpeg_q90` (default): re-save as JPEG quality 90, then score.
- `upload`: resize to max side 1600 px, re-save as JPEG quality 85, then score.
- `native`: score the file as-is (not recommended for comparisons).

## Files

- `model.safetensors`, `config.json`: weights; architecture, per-condition thresholds and training summary.
- `inference.py`, `model_v9.py`: inference script and model definition.
- `requirements.txt`: exact package versions used.
- `code/`: v9 data prep, training, gating and evaluation scripts, plus baseline probes (TruFor, RADAR).
- `reports/report_v7_vs_v9.html`: full v7 vs v9 evaluation report.

## Citation

```bibtex
@misc{obuladinne2026cardamagev9,
  author       = {Sai Charan Obuladinne},
  title        = {Car Damage Photo Integrity Detector v9},
  year         = {2026},
  publisher    = {Hugging Face},
  howpublished = {\url{https://huggingface.co/obuladinnesai/car-damage-photo-integrity-v9}}
}
```
