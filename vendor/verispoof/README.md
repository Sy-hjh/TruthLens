---
language:
- en
- zh
- multilingual
tags:
- audio
- speech
- antispoofing
- deepfake-detection
- source-tracing
- audio-language-model
license: cc-by-nc-4.0
pipeline_tag: audio-text-to-text
base_model:
- openbmb/MiniCPM5-2B
- Qwen/Qwen3-ASR-1.7B
datasets:
- mueller91/MLAAD
- jungjee/spoofceleb
- CodecFake/CodecFake_Plus_Dataset
- isjwdu/DFADD
- openslr/librispeech_asr
- speechcolab/gigaspeech
- AISHELL/AISHELL-3
---

<div align="center">

# VeriSpoof-Plus

**Beyond real or fake: one unified audio LLM for speech deepfake forensics.**

[![arXiv](https://img.shields.io/badge/arXiv-2611.04634-B31B1B?logo=arxiv&logoColor=white)](https://arxiv.org/abs/2611.04634)
[![Demo](https://img.shields.io/badge/%F0%9F%A4%97%20Demo-Space-FFD21E)](https://huggingface.co/spaces/AustinXiao/VeriSpoof-demo)
[![Project Page](https://img.shields.io/badge/Project-Page-000F46)](https://swagshaw.github.io/verispoof/)
[![GitHub](https://img.shields.io/badge/GitHub-Code-181717?logo=github)](https://github.com/swagshaw/verispoof)
[![Benchmark](https://img.shields.io/badge/%F0%9F%A4%97%20Benchmark-VeriSpoof--Bench-FFD21E)](https://huggingface.co/datasets/AustinXiao/VeriSpoof-Bench)
[![License](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey)](https://creativecommons.org/licenses/by-nc/4.0/)

[![Speech-DF-Arena](https://img.shields.io/badge/%F0%9F%A5%87%20Speech--DF--Arena-%231%20open--weight%20%C2%B7%202.14%25%20EER-D4A017)](https://huggingface.co/spaces/Speech-Arena-2025/Speech-DF-Arena)
[![SpoofRadar](https://img.shields.io/badge/%F0%9F%A5%87%20SpoofRadar%20v1.0-%231%20open--weight%20%C2%B7%204.04%25%20EER-D4A017)](https://tefficlabs.com/spoofradar)

</div>

<a href="https://huggingface.co/AustinXiao/VeriSpoof-Plus/resolve/main/assets/verispoof_cover.mp4"><img src="https://huggingface.co/AustinXiao/VeriSpoof-Plus/resolve/main/assets/verispoof_cover.gif" alt="VeriSpoof in 12 seconds: it hears the synthesized word and answers every forensic question with one model" width="100%"></a>

**VeriSpoof-Plus** is an open-weight audio language model for speech deepfake forensics. From a single recording it decides whether the speech is genuine or spoofed, names the system that generated it,
tells whether a second recording comes from the same generator, acoustic model or vocoder, and recognizes the noise,
reverberation and codec of the channel. It explains every decision in short lines that can each be checked against
the audio, and its 2.9 B parameters run on a single 12 GB GPU.

It is the best open-weight detector on both [Speech-DF-Arena](https://huggingface.co/spaces/Speech-Arena-2025/Speech-DF-Arena)
(2.14% pooled EER over 14 test sets, #3 of 28 systems) and [SpoofRadar v1.0](https://tefficlabs.com/spoofradar) (4.04% over
16 test sets). It localizes synthesized spans at 0.16 s resolution, accepts recordings at any sample rate, and with vLLM
reasons over a batch at 0.05 s per recording.

![VeriSpoof-Plus: one model answers five forensic questions; third of 28 systems and first among open-weight ones on Speech-DF-Arena](assets/overview.png)

## News

- **2026-11-04** · VeriSpoof-Plus released, with the [demo](https://huggingface.co/spaces/AustinXiao/VeriSpoof-demo),
  the [benchmark](https://huggingface.co/datasets/AustinXiao/VeriSpoof-Bench) and a two-minute film.
- **2026-11-04** · 🥇🏆 **#1 open-weight on SpoofRadar v1.0**: pooled EER 4.04% over 16 test sets; the next open-weight
  system is at 9.96%.
- **2026-10-31** · 🥇🏆 **#1 open-weight on Speech-DF-Arena**: pooled EER 2.14% over 14 test sets, **#3 of 28 systems**
  overall, behind two proprietary systems (public snapshot of 31 Oct 2026).
- **2026-10-31** · [VeriSpoof-Base](https://huggingface.co/AustinXiao/VeriSpoof-Base) released.

## Highlights

- **Best open-weight deepfake detector.** First among open-weight systems on both Speech-DF-Arena (2.14% pooled EER,
  third of 28 overall) and SpoofRadar v1.0 (4.04%), with less than half the error of the next open-weight system on
  each board.
- **One model, five forensic questions.** The same weights detect spoofed speech, identify the generator (96.8% on
  MLAAD), verify whether two recordings come from the same system (6.17% EER on generators never seen in training),
  and recognize noise, reverberation and codec (81.3%). Every answer is the model's own text answer, scored; there are
  no task-specific heads.
- **Evidence you can check.** The reasoning states bandwidth, noise level, the synthesized span and a decision, each
  line checkable against the audio. The decision follows the evidence: invert the stated span and the decision flips,
  in 100% of tests, also with wording never seen in training.
- **Catches partial fakes.** With reasoning, 99.6% of partially edited recordings in PartialEdit and 97.6% in HAD are
  caught.

## The film

<video controls preload="metadata" poster="https://huggingface.co/AustinXiao/VeriSpoof-Plus/resolve/main/assets/film_poster.jpg" src="https://huggingface.co/AustinXiao/VeriSpoof-Plus/resolve/main/assets/verispoof_film.mp4" width="100%"></video>

*1:59, Chinese and English captions. All voices in the film are synthetic (Fish Audio), including Yang Xiao’s. Music “78 PULSE” by kjartan_abel (CC BY 4.0); sound effects “2 Impact Wet” by original_sound (CC BY 3.0) and “data corrupted” by Saltbearer (CC BY 4.0), the rest CC0, via Openverse and Freesound; recordings from PartialEdit (CC BY 4.0) and MLAAD (CC BY-NC 4.0). Every model output shown is a real VeriSpoof output on that clip. The character is AI-generated art.*

## Base or Plus?

|  | **VeriSpoof-Plus** (this model) | [VeriSpoof-Base](https://huggingface.co/AustinXiao/VeriSpoof-Base) |
|---|---|---|
| Speech-DF-Arena, 14 sets: pooled / mean EER | **2.14 / 1.79%** (#3 of 28) | 4.43 / 4.28% (#4 of 28) |
| SpoofRadar v1.0, 16 sets: pooled / mean EER | **4.04 / 1.65%** | 4.23 / 3.76% |
| Same-generator EER, MLAAD unseen models / unseen architectures | **6.17 / 15.00%** | 13.80 / 20.25% |
| Generator identification (MLAAD) / recording condition | **96.8 / 81.3%** | 95.4 / 75.9% |
| Training data | ≈ 4.4 M utterances | official training splits only, ≈ 0.38 M utterances |

**Use Plus** for the best detection and source verification. **Use Base** for controlled comparisons with models
trained on official training splits only. Training data and recipe: see the
[technical report](https://arxiv.org/abs/2611.04634).

## Model at a glance

| | |
|---|---|
| Parameters | 2.9 B: audio encoder from Qwen3-ASR-1.7B, language model MiniCPM5-2B |
| Input | a speech recording at any sample rate (resampled to 16 kHz) |
| Output | an answer with its score; reasoning lines; a per-token synthetic-speech probability (every 0.16 s) |
| Tasks | detection, generator identification, source verification, recording condition, grounded reasoning |
| Hardware | one CUDA GPU with about 12 GB |

## Quick start

```bash
hf download AustinXiao/VeriSpoof-Plus --include "code/*" --local-dir verispoof
pip install ./verispoof/code
```

```python
from verispoof import VeriSpoof

model = VeriSpoof.from_pretrained("AustinXiao/VeriSpoof-Plus")   # weights are downloaded on first use

# Detection. score = log p(spoof answer) - log p(bona fide answer); label uses threshold 0
model.detect("sample.wav")                        # {'label': 'spoof', 'score': ...}
model.detect(["a.wav", "b.flac"], batch_size=16)  # a list in, a list out; arrays need sr=...

# Grounded reasoning, plus the per-token head (probability that each 0.16 s token is synthesized)
r = model.explain("sample.wav")
print(r["text"])         # OBSERVATIONS / CHANNEL_STATUS / LOCALIZATION / SOURCE_PROFILE / DECISION lines
r["decision"], r["spans"], r["token_prob"]

# Source verification of two spoofed recordings: generator, acoustic_model or vocoder
model.same_source("a.wav", "b.wav", level="generator")   # {'same': ..., 'score': log p(yes) - log p(no)}
model.compare("a.wav", "b.wav")                           # source-verification reasoning

# Closed questions
model.condition("sample.wav", attr="codec")               # also "noise", "reverb"
model.generator("sample.wav", ["XTTS-v2", "Bark", "VITS"])  # candidate systems you supply
```

A probability instead of a score: P(spoof) = sigmoid(0.930 · score − 0.872), calibrated on development data (as in the demo).

### Faster reasoning with vLLM

```bash
pip install "./verispoof/code[vllm]"
```

```python
from verispoof.vllm_backend import VeriSpoofVLLM

if __name__ == "__main__":          # vLLM starts its engine in a separate process
    m = VeriSpoofVLLM.from_pretrained("AustinXiao/VeriSpoof-Plus")
    results = m.explain(["a.wav", "b.wav", "c.wav"])   # batched
    pairs = m.compare([("a.wav", "b.wav"), ("c.wav", "d.wav")])
```

| Reasoning, one A100 | per recording | speed-up |
|---|---:|---:|
| `VeriSpoof.explain`, one at a time | 2.24 s | 1× |
| `VeriSpoofVLLM.explain`, one at a time | 0.50 s | 4.5× |
| `VeriSpoofVLLM.explain`, batch of 64 | 0.05 s | 46× |

Detection scores and the per-token head use `VeriSpoof`. If vLLM fails to load a FlashInfer sampling kernel, set
`VLLM_USE_FLASHINFER_SAMPLER=0`.

## Results

### Speech-DF-Arena leaderboard

Public snapshot of 31 Oct 2026, ordered by pooled EER as on the board; every line of the official protocols
([speech_df_arena](https://github.com/Speech-Arena/speech_df_arena), commit 97a4445) is scored.

| System | Availability | Params | Average EER | Pooled EER |
|---|---|---:|---:|---:|
| Modulate VELMA-2 | Proprietary | 0.3 B | 1.10 | 1.59 |
| Resemble Detect-3B-Omni | Proprietary | 3 B | 2.60 | 2.10 |
| 🥇 **VeriSpoof-Plus (this model)** | **Open-weight** | **2.9 B** | **1.79** | **2.14** |
| Hiya Authenticity Verification | Proprietary | 1 B | 2.11 | 2.32 |
| 🥈 VeriSpoof-Base | Open-weight | 2.9 B | 4.28 | 4.43 |
| DLMSL SpeakSure | Proprietary | 0.7 B | 3.80 | 6.14 |
| Whispeak | Proprietary | 0.1 B | 3.05 | 8.06 |
| DF Arena 1B | Open-weight | 1 B | 5.66 | 9.52 |
| XLS-R + SLS | Open-weight | 0.3 B | 14.01 | 16.08 |

Average = mean of the 14 set EERs. Each VeriSpoof model is ranked on its own (Plus third of 28, Base fourth of 28).

<details>
<summary>Per test set</summary>

| Dataset | Trials | EER (%) | Accuracy (%) |
|---|---:|---:|---:|
| asvspoof_2019 | 71,237 | 0.22 | 99.59 |
| asvspoof_2021_la | 148,176 | 3.44 | 95.81 |
| asvspoof_2021_df | 533,928 | 1.24 | 99.58 |
| asvspoof_2024 | 680,774 | 3.40 | 95.79 |
| in_the_wild | 31,779 | 1.90 | 98.12 |
| fake_or_real | 4,528 | 0.09 | 99.09 |
| codecfake | 304,241 | 0.12 | 99.91 |
| add_2022_track_1 | 109,199 | 8.65 | 89.84 |
| add_2022_track_3 | 126,861 | 1.18 | 99.08 |
| add_2023_round_1 | 111,976 | 0.50 | 99.03 |
| add_2023_round_2 | 118,477 | 2.41 | 97.70 |
| dfadd | 3,755 | 0.00 | 98.59 |
| librisevoc | 92,407 | 0.02 | 99.99 |
| sonar | 3,948 | 1.92 | 96.10 |
| **Average** | | **1.79** | 97.73 |
| **Pooled** | 2,341,286 | **2.14** | |

Accuracy at threshold 0.

</details>

### SpoofRadar v1.0 leaderboard

16 test sets; pooled EER, and accuracy and macro-F1 at the pooled-EER threshold, as SpoofRadar defines them. Other
rows from the published leaderboard (v1.0); ours computed with the same protocol files.

| System | Availability | Pooled EER | Accuracy | Macro-F1 | Average EER |
|---|---|---:|---:|---:|---:|
| Teffic-Audio | Commercial | 1.37 | 98.63 | 98.12 | 1.09 |
| WavLM-L (Teffic) | Closed source | 3.65 | 96.35 | 95.06 | 2.88 |
| 🥇 **VeriSpoof-Plus (this model)** | **Open-weight** | **4.04** | **95.96** | **94.54** | **1.65** |
| 🥈 VeriSpoof-Base | Open-weight | 4.23 | 95.77 | 94.29 | 3.76 |
| Whisper (Teffic) | Closed source | 5.75 | 94.25 | 92.33 | 3.94 |
| DF Arena 500M V1 | Open-weight | 9.96 | 90.04 | 87.08 | 5.19 |
| GRL | Open-weight | 13.25 | 86.75 | 83.17 | 9.90 |

### Beyond detection

On [VeriSpoof-Bench](https://huggingface.co/datasets/AustinXiao/VeriSpoof-Bench); details in the tech report.

| Task | Plus | Base |
|---|---|---|
| Detection, SpoofCeleb / CodecFake+ / CodecFake+ CoSG (unseen generators), EER | **0.10 / 0.65 / 2.34%** | 0.20 / 3.95 / 4.84% |
| Detection under added noise, reverberation and codecs (6 sets), mean EER | **4.22%** | 5.23% |
| Same-generator verification, MLAAD seen / unseen model / unseen architecture, EER | **7.68 / 6.17 / 15.00%** | 17.23 / 13.80 / 20.25% |
| Same-generator verification, SpoofCeleb / STOPA / ASVspoof 2019 LA / ASVspoof 5, EER | 12.20 / **13.55 / 7.62 / 20.65%** | **11.25** / 20.88 / 8.22 / 23.27% |
| Generator identification (MLAAD, closed set) | **96.8%** | 95.4% |
| Acoustic model under an unseen vocoder (SpoofCeleb) | 69.8% | **84.7%** |
| Recording condition (noise / reverberation / codec) | **81.3%** | 75.9% |
| Partial fakes caught after reasoning vs one-step answer (PartialEdit / HAD) | 99.6 vs 94.4 / 97.6 vs 48.4% | 99.6 vs 78.4 / 99.0 vs 99.0% |
| Partial-spoof localization, text spans (HAD / PartialEdit / PartialSpoof), IoU | 0.55 / 0.59 / 0.24 | 0.61 / 0.58 / 0.25 |
| Per-token head (HAD / PartialEdit / PartialSpoof), F1 | 0.91 / 0.79 / 0.77 | 0.91 / 0.79 / 0.74 |
| Decision follows inverted localization (trained / new wording / inserted span) | 1.00 / 1.00 / 1.00 | 1.00 / 0.995 / 1.00 |
| Source-verification reasoning, verdict EER (SpoofCeleb / STOPA / CoSG / LA19 cond.) | **18.40** / 14.35 / 21.80 / **24.55%** | 20.20 / **13.65 / 21.60** / 29.65% |

## Intended use

Research on audio deepfake detection, source tracing and explainable forensics. Not intended as the only basis for
decisions about people; a forensic decision should combine this score with other evidence and human review.

## License

CC BY-NC 4.0 for the weights in this repository (non-commercial use). The base models keep their Apache-2.0 licences
(`LICENSE-Apache-2.0.txt`, `NOTICE`). Some training corpora restrict commercial use; their licences are listed in the
technical report.

## Citation

```bibtex
@misc{verispoof2026,
  title         = {{VeriSpoof}: Beyond Real or Fake with One Audio {LLM}},
  author        = {Xiao, Yang and Dang, Ting},
  year          = {2026},
  eprint        = {2611.04634},
  archivePrefix = {arXiv},
  primaryClass  = {eess.AS},
  url           = {https://arxiv.org/abs/2611.04634}
}
```

## Contact

Yang Xiao, The University of Melbourne, yxiao9550@student.unimelb.edu.au
