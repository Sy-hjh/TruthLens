"""CPU-only bilingual Paraformer adapter, used for a measured Mandarin ASR comparison."""

import json
from functools import lru_cache
import threading
_asr_lock=threading.Lock()
import numpy as np
from bootstrap import ROOT


def available():
    return (ROOT / "models/asr_zh/model.int8.onnx").exists() and (
        ROOT / "models/asr_zh/source.json"
    ).exists()


@lru_cache(maxsize=1)
def _recognizer():
    import sherpa_onnx
    from opencc import OpenCC

    path = ROOT / "models/asr_zh"
    recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
        paraformer=str(path / "model.int8.onnx"),
        tokens=str(path / "tokens.txt"),
        num_threads=2,
        sample_rate=16000,
        feature_dim=80,
        decoding_method="greedy_search",
        debug=False,
        provider="cpu",
    )
    return recognizer

def recognize(samples):
    from opencc import OpenCC
    with _asr_lock:
        return _recognize(samples)

def _recognize(samples):
    path=ROOT / "models/asr_zh"
    from opencc import OpenCC
    recognizer=_recognizer()
    texts = []
    for start in range(0, min(len(samples), 2880000), 480000):
        chunk = samples[start : start + 480000]
        if len(chunk) < 16000 or np.sqrt(np.mean(chunk**2)) < 0.0001:
            continue
        stream = recognizer.create_stream()
        stream.accept_waveform(16000, chunk)
        recognizer.decode_stream(stream)
        texts.append(stream.result.text)
    raw = " ".join(texts)
    return {
        "status": "completed",
        "text": OpenCC("t2s").convert(raw),
        "raw_text": raw,
        "source": json.loads((path / "source.json").read_text()),
        "note": "本地中英双语转写，按30秒分段，最多3分钟；请对照原音核实，支持人工校正。",
    }
