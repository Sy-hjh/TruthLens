"""Independent modality detectors; no remote code and no automatic model downloads."""

import threading, json, subprocess, wave
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from bootstrap import ROOT

lock = threading.Lock()


def available(kind):
    if kind == 'image':
        from .modern_image import configured,available as modern_available
        if configured():return modern_available()
    if kind == 'audio':
        from .voice_forensics import configured,available as modern_available
        if configured():return modern_available()
    if kind == 'video' and (ROOT/'models/active-video.json').exists():
        try:
            info=json.loads((ROOT/'models/active-video.json').read_text())
            if info.get('engine')=='gend-clip':return info.get('approved') is True and (ROOT/'models/gend-clip/model.safetensors').is_file()
            if info.get('engine')=='video-fusion':return info.get('approved') is True and all((ROOT/p).is_file() for p in ('models/video/model.safetensors','models/sifta/model.safetensors',info['head']))
        except (ValueError,OSError,KeyError):return False
    root = ROOT / "models" / kind
    if kind == "asr_zh":
        return (
            (root / "model.int8.onnx").exists()
            and (root / "tokens.txt").exists()
            and (root / "source.json").exists()
        )
    return (root / "model.safetensors").exists() and (root / "source.json").exists()


def classify(kind, data):
    if kind == 'image':
        from .modern_image import configured,predict as modern_predict
        if configured():return modern_predict(data[0])
    if kind == 'audio':
        from .voice_forensics import configured as modern_configured, predict as modern_predict
        if modern_configured():return modern_predict(data)
    if not available(kind):
        raise RuntimeError(f"{kind}模型未安装")
    with lock:
        from transformers import (
            AutoImageProcessor,
            AutoModelForImageClassification,
            VideoMAEImageProcessor,
            VideoMAEForVideoClassification,
            AutoFeatureExtractor,
            AutoModelForAudioClassification,
        )

        path = ROOT / "models" / kind
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if kind == "video":
            processor = VideoMAEImageProcessor.from_pretrained(
                path, local_files_only=True
            )
            model = VideoMAEForVideoClassification.from_pretrained(
                path, local_files_only=True
            )
            release_path = ROOT / 'models/active-video.json'
            release = None
            if release_path.exists() and json.loads(release_path.read_text()).get('engine','video-head') == 'video-head':
                import hashlib
                release = json.loads(release_path.read_text(encoding='utf-8'))
                if release.get('approved') is not True:raise RuntimeError('视频场景模型未通过发布检查')
                head_path = ROOT / release['head']
                if hashlib.sha256(head_path.read_bytes()).hexdigest() != release['head_sha256']:raise RuntimeError('视频分类头校验失败')
                model.classifier.load_state_dict(torch.load(head_path, map_location='cpu', weights_only=True))
                from .faces import face_views
                data, detected = face_views(data)
            inputs = processor(data, return_tensors="pt")
        elif kind == "audio":
            processor = AutoFeatureExtractor.from_pretrained(
                path, local_files_only=True
            )
            model = AutoModelForAudioClassification.from_pretrained(
                path, local_files_only=True
            )
            inputs = processor(
                data, sampling_rate=16000, return_tensors="pt", padding=True
            )
        else:
            processor = AutoImageProcessor.from_pretrained(path, local_files_only=True)
            model = AutoModelForImageClassification.from_pretrained(
                path, local_files_only=True
            )
            inputs = processor(images=data, return_tensors="pt")
        fake = [
            int(k)
            for k, v in model.config.id2label.items()
            if v.lower() in ("fake", "artificial", "ai")
        ]
        if len(fake) != 1:
            raise ValueError("模型标签无法明确映射")
        model = model.to(device).eval()
        with torch.inference_mode():
            score = float(
                model(**inputs.to(device)).logits.softmax(-1)[0, fake[0]].cpu()
            )
        source = json.loads((path / "source.json").read_text(encoding="utf-8"))
        if kind == 'video' and release:
            source = dict(source, repo='亲安人脸场景分类头 / VideoMAE', version=release['version'], face_frames=detected)
        del model
        if device == "cuda":
            torch.cuda.empty_cache()
        return {
            "status": "completed",
            "score": score,
            "source": source,
            "note": "原始模型分数，未经中文老人反诈场景校准；低分不证明真实。",
        }


def audio_samples(path, temp):
    import imageio_ffmpeg

    target = Path(temp) / "audio.wav"
    proc = subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(path),
            "-t",
            "180",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(target),
        ],
        capture_output=True,
        timeout=90,
    )
    if proc.returncode:
        raise ValueError("无法提取音轨或音频格式不可解码")
    with wave.open(str(target), "rb") as f:
        values = (
            np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(
                np.float32
            )
            / 32768
        )
    if len(values) < 16000:
        raise ValueError("音频不足1秒")
    if np.sqrt(np.mean(values**2)) < 0.0001:
        raise ValueError("音轨接近静音，无法做语音核验")
    return values


def transcribe(samples):
    if available("asr_zh"):
        try:
            from .mandarin import recognize

            with lock:
                return recognize(samples)
        except Exception:
            import logging

            logging.exception("Chinese ASR failed, falling back to Whisper")
    if not available("asr") and not available("asr_small"):
        return {"status": "unavailable", "text": "", "note": "语音转写模型未安装"}
    with lock:
        from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq

        path = ROOT / ("models/asr_small" if available("asr_small") else "models/asr")
        processor = AutoProcessor.from_pretrained(path, local_files_only=True)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = (
            AutoModelForSpeechSeq2Seq.from_pretrained(path, local_files_only=True)
            .to(device)
            .eval()
        )
        texts = []
        for start in range(0, min(len(samples), 2880000), 480000):
            chunk = samples[start : start + 480000]
            if len(chunk) < 16000 or np.sqrt(np.mean(chunk**2)) < 0.0001:
                continue
            inputs = processor(
                chunk,
                sampling_rate=16000,
                return_tensors="pt",
                return_attention_mask=True,
            ).to(device)
            with torch.inference_mode():
                tokens = model.generate(**inputs, task="transcribe", max_new_tokens=400)
            texts.append(processor.batch_decode(tokens, skip_special_tokens=True)[0])
        raw_text = " ".join(texts)
        from opencc import OpenCC

        text = OpenCC("t2s").convert(raw_text)
        del model
        if device == "cuda":
            torch.cuda.empty_cache()
        return {
            "status": "completed",
            "text": text,
            "raw_text": raw_text,
            "source": json.loads((path / "source.json").read_text()),
            "note": "按30秒分段转写，最多分析前3分钟，已统一简体；可能识别错误，请对照原音核实。",
        }
