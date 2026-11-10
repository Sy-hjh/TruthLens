---
license: other
tags: [deepfake-detection, video-classification, face-forensics, sifta]
---
# SIFTA deepfake detector: X-CLIP-B/16, fine-tuned on Celeb-DF++

Fine-tuned from `zodumair/sifta-deepfake-detector@89734fc` (FF++ c23 only) on FF++ + Celeb-DF++ training videos. **Research use only.**

- Split: identity-disjoint (18 test-only celebrities), held-out generators HyperReenact, MobileFaceSwap, EDTalk never trained on.
- Calibration from validation only: temperature 1.319, threshold 0.716; risk tiers LOW < 0.3 <= MEDIUM < 0.7 <= HIGH.

| Test set (same videos for both) | Deployed AUC | Fine-tuned AUC | Change (95% CI) |
|---|---|---|---|
| cdfpp_test | 0.7978 | 0.9762 | +0.1784 (+0.158 to +0.201) |
| cdfpp_test_seen_generators | 0.7949 | 0.9765 | +0.1816 (+0.160 to +0.203) |
| cdfpp_test_heldout_generators | 0.8160 | 0.9741 | +0.1580 (+0.128 to +0.190) |
| ffpp_test | 0.9869 | 0.9879 | +0.0010 (-0.011 to +0.010) |
| dfdc | 0.8442 | 0.8244 | -0.0198 (-0.035 to -0.003) |
| celebdf_v2_reference | 0.9116 | 0.9293 | +0.0176 (-0.010 to +0.044) |
| cdfpp_test_FaceReenact | 0.7471 | 0.9803 | +0.2331 (+0.204 to +0.263) |
| cdfpp_test_FaceSwap | 0.9003 | 0.9738 | +0.0735 (+0.055 to +0.092) |
| cdfpp_test_TalkingFace | 0.7314 | 0.9748 | +0.2434 (+0.215 to +0.272) |

Celeb-DF v2 shares its celebrities with Celeb-DF++, so after fine-tuning it is a reference, not a cross-dataset test. DFDC stays clean.
Sees faces only; dataset terms (FF++, Celeb-DF++, DFDC) allow research use only.