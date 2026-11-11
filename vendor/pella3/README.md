---
license: mit
language: en
tags:
  - audio
  - deepfake-detection
  - anti-spoofing
---

# Pellav3: audio deepfake detector

Pellav3 looks at every clip through two views at once: the raw waveform and the mel spectrogram. Each view is encoded into a frame sequence, the two sequences are fused frame by frame into one stream, and attentive statistics pooling turns that stream into a single score.

1.54 billion parameters, 16 kHz input.

## Files

- `pellav3_detector.pt`: the model weights (6.2 GB, fp32).
- `pellav3_infer.py`: ready to run inference script (model class included).
- `config.json`: model identifier.

## Usage

```bash
pip install torch torchaudio transformers==4.48.3 numpy scipy pyloudnorm huggingface_hub
python pellav3_infer.py your_clip.wav
```

The weights are downloaded from the Hub on first use (ffmpeg must be on the PATH). The script prints p_fake per clip and labels a clip FAKE at p_fake of 0.5 or more.

## Previous version

Pellav2 (August 2026): https://huggingface.co/Sadanie/pellav2-audio-deepfake-detector
