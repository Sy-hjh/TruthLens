"""Independent modality detectors; no remote code and no automatic model downloads."""

import threading, json, subprocess, wave
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from bootstrap import ROOT

lock = threading.Lock()


def available(kind):
    if kind == 'audio':
        from .ast_voice import configured as ast_configured, available as ast_available
        if ast_configured():return ast_available()
        from .modern_voice import configured as current_configured,available as current_available
        if current_configured():return current_available()
    if kind == 'image':
        from .product import configured_general, available as product_available
        if configured_general():return product_available(general=True)
        from .modern_image import configured,available as modern_available
        if configured():return modern_available()
    if kind == 'audio':
        from .voice_forensics import configured,available as modern_available
        if configured():return modern_available()
    if kind == 'video' and (ROOT/'models/active-video.json').exists():
        try:
            info=json.loads((ROOT/'models/active-video.json').read_text())
            if info.get('engine')=='video-ordered-head':return info.get('approved') is True and all((ROOT/p).is_file() for p in ('models/gend-clip/model.safetensors',info['head'],info['protocol']))
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
    if kind == 'audio':
        from .ast_voice import configured as ast_configured, predict as ast_predict
        if ast_configured():return ast_predict(data)
        from .modern_voice import configured as current_configured,predict as current_predict
        if current_configured():
            module=current_predict(data)
            return dict(module,score=max(s['score'] for s in module['segments']),threshold=.5)
    if kind == 'image':
        from .product import configured_general, predict as product_predict
        if configured_general():return product_predict(data[0],general=True)
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


class AudioInputError(ValueError):
    def __init__(self,code,message):super().__init__(message);self.code=code

def audio_samples(path, temp):
    import imageio_ffmpeg,re
    import logging
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    container=Path(path).suffix.lower() in {'.mp4','.mov','.avi','.webm','.mkv'}
    def decode(track=0,channel=None):
        cmd=[ffmpeg,'-nostdin','-v','error','-i',str(path),'-t','180','-map',f'0:a:{track}','-vn']
        if channel is not None:cmd+=['-af',f'pan=mono|c0=c{channel}']
        cmd+=['-ac','1','-ar','16000','-f','f32le','pipe:1']
        try:proc=subprocess.run(cmd,capture_output=True,timeout=45)
        except subprocess.TimeoutExpired:raise AudioInputError('decode_timeout','音轨解码超时，不代表视频没有声音。')
        if proc.returncode:
            error=proc.stderr.decode('utf-8',errors='replace')
            logging.warning('Audio decode failure: %s',error[-1000:])
            if 'matches no streams' in error:raise AudioInputError('no_audio_stream','文件中未找到可读取音轨。')
            raise AudioInputError('decode_failed','音轨解码失败，请换MP4/AAC或WAV后重试；不是已确认静音。')
        return np.frombuffer(proc.stdout,dtype=np.float32).copy()
    if container:values=decode()
    else:
        try:
            import soundfile as sf
            from scipy.signal import resample_poly
            import math
            with sf.SoundFile(path) as stream:
                sr=stream.samplerate;x=stream.read(frames=180*sr,dtype='float32',always_2d=True)
            values=x.mean(1)
            if x.shape[1]>1:
                energies=np.sqrt(np.mean(x*x,axis=0));energy=float(np.sqrt(np.mean(values*values)))
                if energy<.05*float(energies.max()):values=x[:,int(energies.argmax())]
            if sr!=16000:
                g=math.gcd(sr,16000);values=resample_poly(values,16000//g,sr//g)
            values=np.asarray(values[:2880000],dtype=np.float32)
        except (ImportError,OSError,RuntimeError,ValueError):values=decode()
    if not np.isfinite(values).all():raise AudioInputError('invalid_audio','音轨包含无效采样，无法分析。')
    if len(values)<16000:raise AudioInputError('too_short','已取得音轨，但不足1秒，无法可靠核验。')
    if np.sqrt(np.mean(values**2))<.0001:
        # A stereo track may cancel in mono. Recover one actual channel before
        # calling it silent; do not amplify invented sound or pad missing audio.
        try:
            recovered=decode(channel=0)
            if len(recovered)>=16000 and np.sqrt(np.mean(recovered**2))>=.0001:values=recovered
            elif container:
                for track in (1,2):
                    try:other=decode(track=track)
                    except AudioInputError:break
                    if len(other)>=16000 and np.sqrt(np.mean(other**2))>=.0001:values=other;break
        except AudioInputError:pass
    if np.sqrt(np.mean(values**2))<.0001:raise AudioInputError('silent','已读取音轨，但采样接近静音；请检查文件音量。')
    return values


def transcribe(samples):
    if available("asr_zh"):
        try:
            from .mandarin import recognize

            return recognize(samples)
        except Exception:
            import logging

            logging.exception("Chinese ASR failed, falling back to Whisper")
    if not available("asr") and not available("asr_small"):
        return {"status": "unavailable", "text": "", "note": "语音转写模型未安装"}
    with lock:
        from transformers.models.auto.processing_auto import AutoProcessor
        from transformers.models.auto.modeling_auto import AutoModelForSpeechSeq2Seq

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
