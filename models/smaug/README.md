---
license: apache-2.0
base_model: google/embeddinggemma-2
base_model_relation: finetune
library_name: sentence-transformers
pipeline_tag: image-classification
tags:
- ai-image-detection
- ai-generated-image-detection
- deepfake-detection
- smaug
- abacusai
---
<div align="center">
  <picture>
      <img src="https://cdn-avatars.huggingface.co/v1/production/uploads/63128dd099791aa61d180c72/dJ6uR23m09M-YEafBpmea.png" width="20%" alt="Smaug-AI-Image-Detector">
  </picture>
</div>
<hr>
<div align="center" style="line-height:1">
  <a href="https://abacus.ai" target="_blank"><img alt="Homepage" src="https://img.shields.io/badge/Homepage-Abacus.AI-white?color=1783ff&logoColor=white"/></a>
  <a href="https://huggingface.co/abacusai" target="_blank"><img alt="Hugging Face" src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Abacus.AI-ffc107?color=ffc107&logoColor=white"/></a>
</div>
<div align="center" style="line-height: 1;">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-Apache_2.0-f5de53?&color=f5de53"/></a>
  <a href="https://huggingface.co/spaces/abacusai/Smaug-AI-Image-Detector" target="_blank"><img alt="Try it in your browser" src="https://img.shields.io/badge/Try_it-in_your_browser-22c55e?&color=22c55e"/></a>
  <a href="https://huggingface.co/abacusai/Smaug-AI-Image-Detector-GGUF" target="_blank"><img alt="GGUF for llama.cpp" src="https://img.shields.io/badge/GGUF-llama.cpp-1783ff?&color=1783ff"/></a>
</div>

## 1. Model Introduction

Smaug-AI-Image-Detector sets a new state of the art for open-source AI-generated image detection. It is a fine-tune of Google's
[EmbeddingGemma-2](https://huggingface.co/google/embeddinggemma-2) by Abacus.AI and the strongest open-source detector
on real-world images.

**A dedicated vision model, 41% smaller than its base.** We streamlined EmbeddingGemma-2 into a vision-only
architecture by removing its 305M-parameter audio tower: 439M parameters instead of 744M, with no loss in accuracy.

```python
import sys
from huggingface_hub import snapshot_download
sys.path.insert(0, snapshot_download("abacusai/Smaug-AI-Image-Detector"))
from smaug_image_detect import SmaugImageDetect     # ships with this repo

detector = SmaugImageDetect.from_pretrained("abacusai/Smaug-AI-Image-Detector")
detector("photo.jpg")                                 # 0.97 -> probability the image is AI-generated
```

## 2. Highlights

- **#1 on real-world images:** 0.973 AUC on OpenFake Reddit; the next best open-source detector scores 0.947.
- **Catches more at the same false-alarm rate:** at 5% false alarms it catches 86.7% of AI images on Reddit;
  the next best catches 77.4%.
- **#1 on OpenFake Core** (0.991 AUC) and **#1 on average** across all three benchmarks (0.982 AUC).
- **Precise:** flags only 3.0% of real Reddit photos, 1.4% of real OpenFake photos and 0.4% of real
  CommunityForensics photos as AI.
- **Current generators:** GPT-Image 2, Nano Banana Pro, Midjourney 7, Seedream 5, FLUX.2, Z-Image, Recraft, Ideogram,
  ERNIE-Image, Sora 2 and Veo 3 frames, DALL·E 3, Firefly 3 and more.
- **Runs anywhere:** at 439M parameters it runs on a single consumer GPU (about 1 GB of memory), on Apple Silicon Macs
  via Metal, or on a plain CPU, so images can be checked locally without sending them anywhere.

## 3. Model Summary

<div align="center">
<table>
<tbody>
<tr><td align="center"><strong>Architecture</strong></td><td align="center">EmbeddingGemma-2 image encoder + linear classifier</td></tr>
<tr><td align="center"><strong>Total Parameters</strong></td><td align="center">439M (base model: 744M)</td></tr>
<tr><td align="center"><strong>Audio Tower</strong></td><td align="center">Removed: vision-only architecture, −305M parameters</td></tr>
<tr><td align="center"><strong>Input</strong></td><td align="center">Any image; scored as three 528 × 528 crops at native resolution</td></tr>
<tr><td align="center"><strong>Output</strong></td><td align="center">Probability that the image is AI-generated</td></tr>
<tr><td align="center"><strong>Hardware</strong></td><td align="center">NVIDIA GPU (~1 GB), Apple Silicon (Metal), or CPU</td></tr>
<tr><td align="center"><strong>Precision</strong></td><td align="center">bfloat16 weights</td></tr>
<tr><td align="center"><strong>Formats</strong></td><td align="center">PyTorch / sentence-transformers (this repo); GGUF for llama.cpp: <a href="https://huggingface.co/abacusai/Smaug-AI-Image-Detector-GGUF">Smaug-AI-Image-Detector-GGUF</a></td></tr>
<tr><td align="center"><strong>Base Model</strong></td><td align="center"><code>google/embeddinggemma-2</code></td></tr>
<tr><td align="center"><strong>Adaptation</strong></td><td align="center">Full fine-tune</td></tr>
</tbody>
</table>
</div>

## 4. Evaluation

<div style="max-width:1100px;margin:0 auto">
<table style="width:100%;table-layout:fixed;border-collapse:collapse;font-size:13px">
<thead><tr><th style="padding:10px 6px;text-align:left;border-bottom:2px solid #2a78d6;width:24%"></th><th style="padding:10px 4px;text-align:center;font-weight:600;border-bottom:2px solid #2a78d6;color:#2a78d6;font-size:13px;background:rgba(42,120,214,0.10);">Smaug-AI-Image-Detector</th><th style="padding:10px 4px;text-align:center;font-weight:500;border-bottom:2px solid #2a78d6;color:#2a78d6;font-size:13px;">OpenFake-SwinV2</th><th style="padding:10px 4px;text-align:center;font-weight:500;border-bottom:2px solid #2a78d6;color:#2a78d6;font-size:13px;">Bombek1-SigLIP-DINOv2</th><th style="padding:10px 4px;text-align:center;font-weight:500;border-bottom:2px solid #2a78d6;color:#2a78d6;font-size:13px;">Thermostatic-Frontier</th><th style="padding:10px 4px;text-align:center;font-weight:500;border-bottom:2px solid #2a78d6;color:#2a78d6;font-size:13px;">CommFor-384</th><th style="padding:10px 4px;text-align:center;font-weight:500;border-bottom:2px solid #2a78d6;color:#2a78d6;font-size:13px;">haywoodsloan-SwinV2</th></tr></thead>
<tbody>
<tr><td colspan="7" style="padding:7px 10px;font-weight:600;color:#1a5fb4;background:#e8f0fc;border-bottom:1px solid rgba(42,120,214,0.2)">AUC ↑</td></tr>
<tr><td style="padding:8px 6px;padding-left:16px;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600">OpenFake Reddit</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600;background:rgba(42,120,214,0.47)"><strong>0.973</strong></td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.42)">0.947</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.23)">0.842</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.32)">0.894</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.05)">0.744</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.33)">0.897</td></tr>
<tr><td style="padding:8px 6px;padding-left:16px;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600">OpenFake Core</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600;background:rgba(42,120,214,0.47)"><strong>0.991</strong></td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.46)">0.989</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.28)">0.959</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.38)">0.977</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.05)">0.921</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.24)">0.953</td></tr>
<tr><td style="padding:8px 6px;padding-left:16px;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600">CommunityForensics</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600;background:rgba(42,120,214,0.43)">0.981</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.29)">0.951</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.47)"><strong>0.990</strong></td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.42)">0.979</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.37)">0.968</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.05)">0.901</td></tr>
<tr><td style="padding:8px 6px;padding-left:16px;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600">Average</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600;background:rgba(42,120,214,0.47)"><strong>0.982</strong></td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.39)">0.962</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.26)">0.930</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.34)">0.950</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.05)">0.878</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.21)">0.917</td></tr>
<tr><td colspan="7" style="padding:7px 10px;font-weight:600;color:#1a5fb4;background:#e8f0fc;border-bottom:1px solid rgba(42,120,214,0.2)">AI images caught at 5% false alarms ↑</td></tr>
<tr><td style="padding:8px 6px;padding-left:16px;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600">OpenFake Reddit</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600;background:rgba(42,120,214,0.47)"><strong>86.7%</strong></td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.40)">77.4%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.21)">54.0%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.26)">60.8%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.05)">34.8%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.25)">59.4%</td></tr>
<tr><td style="padding:8px 6px;padding-left:16px;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600">OpenFake Core</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600;background:rgba(42,120,214,0.47)"><strong>95.8%</strong></td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.46)">95.0%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.29)">83.9%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.35)">87.9%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.05)">68.2%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.28)">83.1%</td></tr>
<tr><td style="padding:8px 6px;padding-left:16px;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600">CommunityForensics</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600;background:rgba(42,120,214,0.39)">92.2%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.19)">81.8%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.47)"><strong>96.2%</strong></td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.38)">91.6%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.22)">83.2%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.05)">74.5%</td></tr>
<tr><td colspan="7" style="padding:7px 10px;font-weight:600;color:#1a5fb4;background:#e8f0fc;border-bottom:1px solid rgba(42,120,214,0.2)">Real photos flagged as AI ↓</td></tr>
<tr><td style="padding:8px 6px;padding-left:16px;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600">OpenFake Reddit</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600;background:rgba(42,120,214,0.46)">3.0%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.46)">2.9%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.05)">34.7%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.28)">16.4%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.47)"><strong>2.0%</strong></td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.37)">9.5%</td></tr>
<tr><td style="padding:8px 6px;padding-left:16px;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600">OpenFake Core</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600;background:rgba(42,120,214,0.44)">1.4%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.43)">2.1%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.05)">18.4%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.32)">6.6%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.47)"><strong>0.3%</strong></td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.45)">1.1%</td></tr>
<tr><td style="padding:8px 6px;padding-left:16px;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600">CommunityForensics</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;font-weight:600;background:rgba(42,120,214,0.47)"><strong>0.4%</strong></td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.41)">3.0%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.35)">5.2%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.05)">17.7%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.38)">4.0%</td><td style="padding:8px 6px;text-align:center;border-bottom:1px solid rgba(128,128,128,0.15);font-size:14px;background:rgba(42,120,214,0.22)">10.6%</td></tr>
</tbody></table>
</div>
<div style="font-size:11.5px;color:#6B6B6B;margin-top:6px">Bold = best in the row. Shading is relative within each row (darker = better). All models scored on the same 26,070 test images.</div>

<details>
<summary><b>All open-source detectors tested</b></summary>

| Model | OpenFake Reddit | OpenFake Core | CommunityForensics | Average | Real photos flagged: Reddit / Core / CF |
|---|---|---|---|---|---|
| **Smaug-AI-Image-Detector** | 0.9730 | 0.9909 | 0.9808 | 0.9816 | 3.0% / 1.4% / 0.4% |
| [OpenFake-SwinV2](https://github.com/vicliv/OpenFake) | 0.9467 | 0.9886 | 0.9512 | 0.9622 | 2.9% / 2.1% / 3.0% |
| [s-gehring/detectra-openfake](https://huggingface.co/s-gehring/detectra-openfake) | 0.9359 | 0.9715 | 0.9535 | 0.9537 | 2.7% / 1.2% / 2.0% |
| [Thermostatic-Frontier](https://huggingface.co/Thermostatic/community-forensics-frontier-detector-2026-08) | 0.8935 | 0.9766 | 0.9792 | 0.9498 | 16.4% / 6.6% / 17.7% |
| [Bombek1-SigLIP-DINOv2](https://huggingface.co/Bombek1/ai-image-detector-siglip-dinov2) | 0.8418 | 0.9591 | 0.9900 | 0.9303 | 34.7% / 18.4% / 5.2% |
| [haywoodsloan-SwinV2](https://huggingface.co/haywoodsloan/ai-image-detector-deploy) | 0.8970 | 0.9528 | 0.9011 | 0.9170 | 9.5% / 1.1% / 10.6% |
| [TensorFold/detectra-v1](https://huggingface.co/TensorFold/detectra-v1) | 0.7483 | 0.9330 | 0.9652 | 0.8822 | 5.3% / 0.6% / 3.5% |
| [CommFor-384](https://huggingface.co/OwensLab/commfor-model-384) | 0.7441 | 0.9214 | 0.9678 | 0.8778 | 2.0% / 0.3% / 4.0% |
| [Ateeqq/ai-vs-human-image-detector](https://huggingface.co/Ateeqq/ai-vs-human-image-detector) | 0.8665 | 0.9045 | 0.6939 | 0.8217 | 27.2% / 14.3% / 40.1% |
| [Organika/sdxl-detector](https://huggingface.co/Organika/sdxl-detector) | 0.6625 | 0.6673 | 0.8243 | 0.7180 | 43.9% / 22.4% / 24.8% |
| [umm-maybe/AI-image-detector](https://huggingface.co/umm-maybe/AI-image-detector) | 0.7364 | 0.6007 | 0.6042 | 0.6471 | 13.8% / 17.3% / 15.3% |

</details>

## 5. Training Approach

- **Full fine-tune** of EmbeddingGemma-2's image encoder with a linear classifier on its embedding.
- **Native-resolution crops** keep the pixel-level traces that generators leave, instead of shrinking the image.
- **Robustness training** with resizing, recompression and blur, so scores hold up on shared and re-saved copies.
- **Hard negatives** from professional photography, so a polished real photo is not mistaken for AI.

## 6. Limitations

- Brand-new generators, or ones built to evade detectors, may get through.
- A real photo with a small AI-edited region may be scored as real.
- A score is evidence, not proof: do not use it as the only basis for decisions about people or their work.

## 7. Usage

```bash
pip install "sentence-transformers[image]" pillow
```

```python
from huggingface_hub import snapshot_download
import sys

path = snapshot_download("abacusai/Smaug-AI-Image-Detector")
sys.path.insert(0, path)
from smaug_image_detect import SmaugImageDetect

detector = SmaugImageDetect.from_pretrained(path)        # NVIDIA GPU, Apple Silicon (Metal) or CPU, picked automatically
detector("photo.jpg")                                     # -> float in [0, 1]
detector(["a.jpg", "b.png", pil_image], batch_size=16)   # -> list of floats
detector("photo.jpg", crops=1)                            # 3x faster
```

0.5 is a good default threshold; raise it when a false alarm is costly.

**llama.cpp:** use [Smaug-AI-Image-Detector-GGUF](https://huggingface.co/abacusai/Smaug-AI-Image-Detector-GGUF). It includes the classification head and a client that applies the same crops; a GGUF of the image encoder alone returns an embedding, not a verdict.

## 8. License

Apache 2.0, the same license as the base model, EmbeddingGemma-2.

## 9. Citation

```bibtex
@misc{abacusai2026smaugaiimagedetector,
  title  = {Smaug-AI-Image-Detector},
  author = {Abacus.AI},
  year   = {2026},
  url    = {https://huggingface.co/abacusai/Smaug-AI-Image-Detector}
}
```

