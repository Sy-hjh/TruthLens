# Data card: SIFTA deepfake detector v1
| Role | Dataset | Videos | Notes |
|---|---|---|---|
| train/val/test | FaceForensics++ c23 (Kaggle mirror xdxd003/ff-c23; official split 720/140/140 pairs) | 4,320 / 840 / 840 | DeepFakeDetection excluded (no real counterparts) |
| cross-dataset test | Celeb-DF v2 official test list | 518 | test only |
| cross-dataset test | DFDC parts 0-9 (Kaggle mirror pranay22077/dfdc-10), 1,000 real + 1,000 scene-matched fakes | 2,000 | test only; manifest dfdc_test_v1.csv |
| final real-world test | Deepfake-Eval-2024 (nuriachandra/Deepfake-Eval-2024) | all real/fake-labelled videos | evaluation only (dataset terms) |

Face clips: YuNet detector, 8 frames (stride 2) per clip, 1.3x margin, 256 px. Train: 10 clips per real / 2 per fake video (class-balanced frames).
