"""
Hugging Face Inference Endpoint handler for the SIFTA deepfake detector (X-CLIP-B/16, Decision 019).

Reproduces the training preprocessing exactly (notebook 01, crops_v1):
  video -> 4 clips of 8 frames (stride 2) spread over 5-95 % of the video
        -> YuNet face detection on the clip's middle/first/last frame, one fixed box per face for the clip
        -> square crop, 1.3x margin, 256 px, JPEG q92 round-trip, RGB
        -> resize 224, ImageNet normalisation -> X-CLIP video encoder + head
        -> temperature-scaled P(fake); video score = mean over the largest face's clips

Request:  {"inputs": <base64 video>, "parameters": {"details": false}}   (raw video bytes also accepted)
Response: [{"label": "FAKE", "score": p}, {"label": "REAL", "score": 1 - p}]   ([] if no face is found)
          with "details": true -> a dict with risk tier, per-face scores, clips scored and the threshold,
          plus (added for the SIFTA app) "clips" (score per sampled moment and face), "face_thumbs"
          (128 px JPEG base64 of each face) and "fps". No face + details -> {"error": "no_face_detected", ...}.
"""
import base64
import json
import os
import tempfile

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from safetensors.torch import load_file

CLIP_LEN, CLIP_STRIDE, CLIPS_PER_VIDEO = 8, 2, 4
CROP_SIZE, MARGIN, JPEG_Q = 256, 1.3, 92
DET_SCORE, DET_MAX_SIDE, MAX_FACES = 0.6, 640, 2
SEQ_MAX_FRAMES = 1500


class XCLIPDetector(nn.Module):
    # identical module layout to training (vision / proj / mit / head), so the state dict loads 1:1
    def __init__(self, config):
        super().__init__()
        from transformers import XCLIPModel
        m = XCLIPModel(config)
        self.vision, self.proj, self.mit = m.vision_model, m.visual_projection, m.mit
        self.num_frames = config.vision_config.num_frames
        self.head = nn.Sequential(nn.Dropout(0.1), nn.Linear(config.projection_dim, 2))

    def forward(self, x):                      # (B, T, C, H, W)
        b, t = x.shape[:2]
        cls = _pooled(self.vision(pixel_values=x.flatten(0, 1), return_dict=True))
        emb = self.proj(cls).view(b, t, -1)
        return self.head(_pooled(self.mit(emb, return_dict=True)))


def _pooled(out):
    # transformers 4.x: the MIT block returns a tuple (last_hidden_state, pooler_output, ...) by default
    return out.pooler_output if hasattr(out, "pooler_output") else out[1]


class EndpointHandler:
    def __init__(self, path=""):
        from transformers import XCLIPConfig
        self.cfg = json.load(open(os.path.join(path, "sifta_config.json")))
        xcfg = XCLIPConfig.from_json_file(os.path.join(path, "xclip_config.json"))
        self.model = XCLIPDetector(xcfg)
        missing, unexpected = self.model.load_state_dict(load_file(os.path.join(path, "model.safetensors")), strict=False)
        assert not missing and not unexpected, f"weights do not match the model: missing={missing[:3]} unexpected={unexpected[:3]}"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device).eval()
        self.size = int(self.cfg.get("image_size", 224))
        self.mean = torch.tensor(self.cfg["mean"]).view(1, 3, 1, 1)
        self.std = torch.tensor(self.cfg["std"]).view(1, 3, 1, 1)
        self.T = float(self.cfg["temperature"])
        self.threshold = float(self.cfg["threshold"])
        self.bands = self.cfg.get("risk_bands", [0.3, 0.7])
        cv2.setNumThreads(1)
        self.det = cv2.FaceDetectorYN.create(os.path.join(path, "face_detection_yunet_2023mar.onnx"), "", (320, 320), DET_SCORE, 0.3, 50)

    # ── face clips (same as training) ─────────────────────────────────────────
    def _detect(self, img):
        h, w = img.shape[:2]
        s = min(1.0, DET_MAX_SIDE / max(h, w))
        small = cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA) if s < 1 else img
        self.det.setInputSize((small.shape[1], small.shape[0]))
        _, f = self.det.detect(small)
        if f is None:
            return []
        return sorted([(r[0] / s, r[1] / s, r[2] / s, r[3] / s, float(r[14])) for r in f], key=lambda b: -b[2] * b[3])

    @staticmethod
    def _iou(a, b):
        ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
        iw = max(0.0, min(ax2, bx2) - max(a[0], b[0])); ih = max(0.0, min(ay2, by2) - max(a[1], b[1]))
        inter = iw * ih
        return inter / (a[2] * a[3] + b[2] * b[3] - inter + 1e-9)

    def _tracks(self, frames):
        probes = [len(frames) // 2, 0, len(frames) - 1]
        dets = {i: self._detect(frames[i]) for i in probes}
        anchor = next((i for i in probes if dets[i]), None)
        if anchor is None:
            return []
        out = []
        for a in dets[anchor][:MAX_FACES]:
            boxes = [a[:4]]
            for i in probes:
                if i != anchor and dets[i]:
                    b = max(dets[i], key=lambda d: self._iou(a, d))
                    if self._iou(a, b) > 0.3:
                        boxes.append(b[:4])
            out.append(tuple(np.median(np.array(boxes), axis=0)))
        return out

    @staticmethod
    def _crop(img, box):
        x, y, w, h = box[:4]
        side = max(w, h) * MARGIN; cx, cy = x + w / 2, y + h / 2
        x0, y0, s = int(round(cx - side / 2)), int(round(cy - side / 2)), int(round(side))
        H, W = img.shape[:2]
        pad = max(0, -x0, -y0, x0 + s - W, y0 + s - H)
        if pad:
            img = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
            x0, y0 = x0 + pad, y0 + pad
        crop = cv2.resize(img[y0:y0 + s, x0:x0 + s], (CROP_SIZE, CROP_SIZE),
                          interpolation=cv2.INTER_AREA if s > CROP_SIZE else cv2.INTER_CUBIC)
        ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, JPEG_Q])       # same JPEG round-trip as the training crops
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)[:, :, ::-1].copy()                  # RGB

    @staticmethod
    def _starts(total):
        span = (CLIP_LEN - 1) * CLIP_STRIDE + 1
        if total < span:
            return []
        lo = int(0.05 * total); hi = max(lo, min(int(0.95 * total), total) - span)
        return sorted(set(np.linspace(lo, hi, CLIPS_PER_VIDEO).round().astype(int).tolist()))

    def _read_clips(self, path):
        cap = cv2.VideoCapture(path)
        try:
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            starts = self._starts(total)
            clips = {}
            if total <= SEQ_MAX_FRAMES:
                want = {}
                for st in starts:
                    for k in range(CLIP_LEN):
                        want.setdefault(st + k * CLIP_STRIDE, []).append(st)
                got = {st: [] for st in starts}
                for idx in range(max(want) + 1 if want else 0):
                    if not cap.grab():
                        break
                    if idx in want:
                        ok, fr = cap.retrieve()
                        if ok:
                            for st in want[idx]:
                                got[st].append(fr)
                clips = {st: v for st, v in got.items() if len(v) == CLIP_LEN}
            else:
                for st in starts:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, st); fr_list = []
                    for k in range((CLIP_LEN - 1) * CLIP_STRIDE + 1):
                        ok, fr = cap.read()
                        if not ok:
                            break
                        if k % CLIP_STRIDE == 0:
                            fr_list.append(fr)
                    if len(fr_list) == CLIP_LEN:
                        clips[st] = fr_list
            self._fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
            return [(s, clips[s]) for s in sorted(clips)], total
        finally:
            cap.release()

    def _tensor(self, crops):
        x = torch.from_numpy(np.stack(crops)).permute(0, 3, 1, 2).float() / 255.0      # (8, 3, 256, 256)
        x = F.interpolate(x, size=(self.size, self.size), mode="bilinear", antialias=True, align_corners=False)
        return (x - self.mean) / self.std

    # ── request ───────────────────────────────────────────────────────────────
    def __call__(self, data):
        inp = data.get("inputs", data) if isinstance(data, dict) else data
        params = (data.get("parameters") or {}) if isinstance(data, dict) else {}
        raw = inp if isinstance(inp, (bytes, bytearray)) else base64.b64decode(inp.split(",", 1)[-1])
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(raw); path = f.name
        try:
            clips, total = self._read_clips(path)
        finally:
            os.remove(path)
        per_face, moments, thumbs = {}, [], {}
        for ci, (start, frames) in enumerate(clips):
            for fi, box in enumerate(self._tracks(frames)):
                crops = [self._crop(fr, box) for fr in frames]
                x = self._tensor(crops).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    p = torch.softmax(self.model(x).float() / self.T, -1)[0, 1].item()
                per_face.setdefault(fi, []).append(p)
                moments.append({"clip": ci, "face": fi, "start_frame": int(start),
                                "face_px": int(max(box[2], box[3])), "p_fake": round(p, 4)})
                if fi not in thumbs and params.get("details"):
                    mid = cv2.resize(crops[len(crops) // 2][:, :, ::-1], (128, 128), interpolation=cv2.INTER_AREA)
                    ok, buf = cv2.imencode(".jpg", mid, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    thumbs[fi] = base64.b64encode(buf.tobytes()).decode("ascii")
        if 0 not in per_face:
            return {"error": "no_face_detected", "frames": total, "clips_read": len(clips),
                    "fps": self._fps} if params.get("details") else []
        p_fake = float(np.mean(per_face[0]))
        p_max = float(max(np.mean(v) for v in per_face.values()))
        if not params.get("details"):
            return [{"label": "FAKE", "score": p_fake}, {"label": "REAL", "score": 1.0 - p_fake}]
        tier = "LOW" if p_fake < self.bands[0] else ("MEDIUM" if p_fake < self.bands[1] else "HIGH")
        return {"label": "FAKE" if p_fake >= self.threshold else "REAL", "p_fake": p_fake, "p_fake_max_face": p_max,
                "risk_tier": tier, "threshold": self.threshold, "faces": len(per_face), "clips_scored": len(per_face[0]),
                "frames": total, "model": self.cfg.get("display", "X-CLIP-B/16"),
                "clips": moments, "face_thumbs": [thumbs[k] for k in sorted(thumbs)], "fps": self._fps}
