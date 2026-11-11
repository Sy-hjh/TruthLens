"""Pellav3 audio deepfake detector: minimal inference code.

    pip install torch torchaudio transformers==4.48.3 numpy scipy pyloudnorm huggingface_hub   (and ffmpeg on the PATH)
    python pellav3_infer.py clip1.wav clip2.mp3 ...

The weights are downloaded from the Hugging Face Hub on first use. To run from a local copy instead, pass it first:
python pellav3_infer.py pellav3_detector.pt clip1.wav ...

The model reads each 4 second window with two speech encoders, XLS-R 1B on the waveform and w2v-BERT 2.0 on a mel
spectrogram, fuses their frames moment by moment and pools them into one score. A clip of 4 seconds or less is scored
once; a longer clip is scored in 4 second windows every 2 seconds (the last window ends at the end of the clip) and the
window logits are averaged.
"""
import math
import subprocess
import sys
import time

import numpy as np
import torch
import torch.nn as nn

SR = 16000
CROP_S = 4.0
CROP = int(CROP_S * SR)
TARGET_LUFS = -23.0
HUB_REPO = "Sadanie/pellav3-audio-deepfake-detector"
WEIGHTS = "pellav3_detector.pt"
XLSR = "facebook/wav2vec2-xls-r-1b"
W2VBERT = "facebook/w2v-bert-2.0"


class Res2Block(nn.Module):
    def __init__(self, c=256, scale=4, k=3, d=2):
        super().__init__()
        self.scale, w = scale, c // scale
        self.convs = nn.ModuleList([nn.Conv1d(w, w, k, padding=d * (k - 1) // 2, dilation=d) for _ in range(scale - 1)])
        self.norm = nn.LayerNorm(c)

    def forward(self, x, m):
        xs = torch.chunk(x, self.scale, dim=1)
        out, y = [xs[0]], None
        for i in range(1, self.scale):
            y = torch.relu(self.convs[i - 1](xs[i] if y is None else xs[i] + y)) * m
            out.append(y)
        return (self.norm(torch.cat(out, 1).transpose(1, 2)).transpose(1, 2) + x) * m


class XlsrBranch(nn.Module):
    """XLS-R 1B on the standardised waveform; a learned mix of all layer outputs -> frames [B, F, 1280]"""
    def __init__(self):
        super().__init__()
        from transformers import Wav2Vec2Config, Wav2Vec2Model
        self.backbone = Wav2Vec2Model(Wav2Vec2Config.from_pretrained(XLSR))
        self.layer_weights = nn.Parameter(torch.zeros(self.backbone.config.num_hidden_layers + 1))
        self.head = nn.Linear(self.backbone.config.hidden_size, 1)      # the branch's own head, kept for the weights file, unused

    def frames(self, wav):
        wav = (wav - wav.mean(1, keepdim=True)) / (wav.std(1, keepdim=True) + 1e-7)
        hs = self.backbone(wav, output_hidden_states=True).hidden_states
        w = torch.softmax(self.layer_weights, dim=0)
        return torch.stack(hs).mul(w[:, None, None, None]).sum(0)


class W2vBertBranch(nn.Module):
    """w2v-BERT 2.0 on 80-bin mel features of the real part of the clip; layer mix, projection, two Res2 blocks -> [B, F, 256]"""
    def __init__(self):
        super().__init__()
        from transformers import Wav2Vec2BertConfig, Wav2Vec2BertModel
        self.backbone = Wav2Vec2BertModel(Wav2Vec2BertConfig.from_pretrained(W2VBERT))
        self.layer_weights = nn.Parameter(torch.zeros(self.backbone.config.num_hidden_layers + 1))
        dim = self.backbone.config.hidden_size
        self.ms_proj = nn.Linear(dim, 256)
        self.ms_blocks = nn.ModuleList([Res2Block(256, 4, 3, 2), Res2Block(256, 4, 3, 3)])
        self.att = nn.Sequential(nn.Linear(256, 128), nn.Tanh(), nn.Linear(128, 1))   # the branch's own pooling and head,
        self.head = nn.Linear(512, 1)                                                  # kept for the weights file, unused

    @staticmethod
    def features(wav):
        import torchaudio.compliance.kaldi as K
        feats, lens = [], []
        with torch.autocast(device_type=wav.device.type, enabled=False):
            for x in wav.float():
                nz = torch.nonzero(x).flatten()
                n_s = int(nz[-1]) + 1 if len(nz) else len(x)
                f = K.fbank(x[None, :max(n_s, 400)] * 32768.0, num_mel_bins=80, sample_frequency=SR, dither=0.0, window_type="povey")
                f = (f - f.mean(0, keepdim=True)) / torch.sqrt(f.var(0, keepdim=True) + 1e-7)
                n = f.shape[0] // 2 * 2
                feats.append(f[:n].reshape(n // 2, 160))
                lens.append(n // 2)
        F = max(lens)
        out = torch.zeros(len(feats), F, 160, device=wav.device)
        mask = torch.zeros(len(feats), F, dtype=torch.long, device=wav.device)
        for i, (f, n) in enumerate(zip(feats, lens)):
            out[i, :n] = f
            mask[i, :n] = 1
        return out, mask

    def frames(self, wav):
        feats, mask = self.features(wav)
        mask[mask.sum(1) == 0, 0] = 1
        m = mask[:, :, None].float()
        hs = self.backbone(input_features=feats, attention_mask=mask, output_hidden_states=True).hidden_states
        w = torch.softmax(self.layer_weights, dim=0)
        h = torch.stack(hs).mul(w[:, None, None, None]).sum(0)
        z = self.ms_proj(h.float()) * m
        zt, mt = z.transpose(1, 2), m.transpose(1, 2)
        for b in self.ms_blocks:
            zt = b(zt, mt)
        return zt.transpose(1, 2), mask


class Detector(nn.Module):
    """the two branches, their frames side by side per moment (512), two shared Res2 blocks, attentive statistics pooling"""
    def __init__(self):
        super().__init__()
        self.xl = XlsrBranch()
        self.w2v = W2vBertBranch()
        self.x_proj = nn.Linear(1280, 256)
        self.x_blocks = nn.ModuleList([Res2Block(256, 4, 3, 2), Res2Block(256, 4, 3, 3)])
        self.f_blocks = nn.ModuleList([Res2Block(512, 4, 3, 2), Res2Block(512, 4, 3, 3)])
        self.att = nn.Sequential(nn.Linear(512, 128), nn.Tanh(), nn.Linear(128, 1))
        self.head = nn.Linear(1024, 1)

    def forward(self, wav):
        hx = self.xl.frames(wav)                                      # [B, Fx, 1280]
        zw, mw = self.w2v.frames(wav)                                 # [B, Fw, 256], [B, Fw]
        B = wav.shape[0]
        zx = self.x_proj(hx.float())
        zxt, mxt = zx.transpose(1, 2), torch.ones(B, 1, hx.shape[1], device=wav.device)
        for b in self.x_blocks:
            zxt = b(zxt, mxt)
        zx = zxt.transpose(1, 2)
        F = min(zx.shape[1], zw.shape[1])
        zx, zw, m = zx[:, :F], zw[:, :F].float(), mw[:, :F]
        zt, mt = torch.cat([zx, zw], dim=2).transpose(1, 2), m[:, None, :].float()
        for b in self.f_blocks:
            zt = b(zt, mt)
        z = zt.transpose(1, 2)
        a = torch.softmax(self.att(z).squeeze(-1).masked_fill(m == 0, float("-inf")), dim=1)[:, :, None]
        mu = (a * z).sum(1)
        var = (a * z ** 2).sum(1) - mu ** 2
        return self.head(torch.cat([mu, torch.sqrt(var.clamp(min=1e-6))], dim=1)).squeeze(-1)


def decode(path, start=0.0, dur=None):
    a = (["-ss", f"{start:.3f}"] if start > 0 else []) + (["-t", f"{dur:.3f}"] if dur else [])
    r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + a + ["-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace")[-300:])
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def loudness(x):
    try:
        import pyloudnorm as pyln

        if len(x) >= int(0.4 * SR):
            v = pyln.Meter(SR).integrated_loudness(x.astype(np.float64))
            if np.isfinite(v):
                return float(v)
    except Exception:
        pass
    return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9) - 0.691)


def view(x):
    """mean removal and 20 Hz high-pass, centre 4 s crop, loudness to -23 LUFS, zero-pad to 4 s"""
    from scipy.signal import butter, sosfiltfilt

    x = x - x.mean()
    if len(x) > 3 * SR // 100:
        x = sosfiltfilt(butter(2, 20.0, btype="highpass", fs=SR, output="sos"), x)
    x = x.astype(np.float32)
    if len(x) > CROP:
        off = (len(x) - CROP) // 2
        x = x[off:off + CROP]
    if len(x):
        gain = float(np.clip(TARGET_LUFS - loudness(x), -40.0, 40.0))
        x = np.clip(x * 10 ** (gain / 20), -1.0, 1.0).astype(np.float32)
    if len(x) < CROP:
        x = np.concatenate([x, np.zeros(CROP - len(x), np.float32)])
    return x


def views(path):
    """one view for a clip of 4 s or less; otherwise one per 4 s window every 2 s, the last ending at the end of the clip"""
    whole = decode(path)
    d = len(whole) / SR
    if d <= CROP_S:
        return [view(whole)], d
    starts = sorted({round(min(k * 2.0, d - CROP_S), 3) for k in range(math.ceil((d - CROP_S) / 2.0) + 1)})
    return [view(decode(path, s, CROP_S)) for s in starts], d


def hub_weights():
    from huggingface_hub import hf_hub_download

    hf_hub_download(HUB_REPO, "config.json")
    return hf_hub_download(HUB_REPO, WEIGHTS)


def load_model(weights=None, device=None):
    device = device or ("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    model = Detector().to(device)
    sd = torch.load(weights or hub_weights(), map_location=device)
    model.load_state_dict(sd["model"] if "model" in sd else sd, strict=True)
    return model.eval(), device


@torch.no_grad()
def score(model, device, path):
    """-> (logit averaged over the clip's views, duration in s, seconds of model time)"""
    vs, d = views(path)
    t0 = time.time()
    with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
        z = model(torch.from_numpy(np.stack(vs)).to(device)).float()
    if device == "cuda":
        torch.cuda.synchronize()
    return float(z.mean()), d, time.time() - t0


def main():
    args = sys.argv[1:]
    weights = args.pop(0) if args and args[0].endswith(".pt") else None
    model, device = load_model(weights)
    for f in args:
        z, _, _ = score(model, device, f)
        p = 1 / (1 + math.exp(-z))
        print(f"{f}: p_fake={p:.3f} -> {'FAKE' if p >= 0.5 else 'real'}")


if __name__ == "__main__":
    main()
