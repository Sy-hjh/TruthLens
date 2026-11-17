"""Local inference for the supplied TruthLens AST encoder and Qwen-adapted head."""

import hashlib
import json

import numpy as np
import torch

from bootstrap import ROOT

RATE = 16000
FRAMES = 400
CONFIG = ROOT / 'models/active-audio.json'


def configured():
    if not CONFIG.is_file():
        return False
    return json.loads(CONFIG.read_text(encoding='utf-8')).get('engine') == 'ast-qwen'


def available():
    try:
        info = json.loads(CONFIG.read_text(encoding='utf-8'))
        return info['engine'] == 'ast-qwen' and all(
            (ROOT / info['directory'] / name).is_file()
            for name in ('config.json', 'model.safetensors', 'ast_adapted.npz')
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def predict(samples):
    from safetensors.torch import load_file
    from torchaudio.compliance.kaldi import fbank
    from transformers import ASTConfig, ASTModel
    from .detector import lock

    info = json.loads(CONFIG.read_text(encoding='utf-8'))
    directory = ROOT / info['directory']
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    dtype = torch.float16 if device.type == 'cuda' else torch.float32
    mono = np.asarray(samples[:RATE * 4], dtype=np.float32)
    if not mono.size or not np.isfinite(mono).all():
        raise ValueError('没有可供声音核验的有效采样')
    seconds = len(mono) / RATE
    mono = np.pad(mono, (0, max(0, 400 - len(mono))))
    features = fbank(
        torch.from_numpy(mono[None, :]), sample_frequency=RATE, num_mel_bins=128,
        window_type='hanning', htk_compat=True, use_energy=False, dither=0.0,
    )
    features = torch.nn.functional.pad(features, (0, 0, 0, FRAMES - len(features)))
    features = (features + 4.2677393) / (2 * 4.5689974)

    with lock:
        for name, expected in info['sha256'].items():
            digest = hashlib.sha256()
            with (directory / name).open('rb') as source:
                for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                    digest.update(block)
            if digest.hexdigest() != expected:
                raise ValueError('声音模型文件校验失败')
        config = ASTConfig.from_pretrained(directory, local_files_only=True)
        config._attn_implementation = 'sdpa'
        model = ASTModel(config)
        prefix = 'audio_spectrogram_transformer.'
        weights = load_file(directory / 'model.safetensors')
        model.load_state_dict({key[len(prefix):]: value for key, value in weights.items() if key.startswith(prefix)})
        del weights
        positions = model.embeddings.position_embeddings.detach()
        bands = (config.num_mel_bins - config.patch_size) // config.frequency_stride + 1
        time_steps = (FRAMES - config.patch_size) // config.time_stride + 1
        cropped = positions[:, 2:].reshape(1, bands, -1, config.hidden_size)[:, :, :time_steps]
        model.embeddings.position_embeddings = torch.nn.Parameter(torch.cat(
            (positions[:, :2], cropped.reshape(1, -1, config.hidden_size)), dim=1,
        ))
        model = model.to(device=device, dtype=dtype).eval()
        with torch.inference_mode(), np.load(directory / 'ast_adapted.npz', allow_pickle=False) as head:
            pooled = model(features[None, :].to(device=device, dtype=dtype)).pooler_output.float().cpu().numpy()
            normalized = (pooled - head['center']) / head['scale']
            logit = (normalized @ head['weights'].T + head['intercept']).item()
            score = float(1 / (1 + np.exp(-np.clip(logit, -700, 700))))
        del model
        if device.type == 'cuda':
            torch.cuda.empty_cache()

    if not np.isfinite(score):
        raise ValueError('声音模型未返回有效分数')
    threshold = float(info['threshold'])
    source = {'repo': 'TruthLens AST / 千问仿声适配头', 'version': info['version']}
    segment = {'start': 0, 'end': seconds, 'score': score, 'threshold': threshold, 'source': source}
    return {
        'status': 'completed', 'analysis_basis': 'acoustic_waveform_only',
        'sample_rate': RATE, 'analyzed_seconds': seconds, 'segments': [segment],
        'score': score, 'threshold': threshold, 'source': source,
        'note': '使用提供的 AST 权重分析开头最多 4 秒的声音合成线索，适配范围以随模型提供的千问仿声评测为准。',
    }
