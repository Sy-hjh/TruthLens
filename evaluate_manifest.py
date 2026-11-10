"""Independent real/fake evaluation for authorized video or audio manifests."""

import bootstrap
import argparse, json, tempfile
from pathlib import Path
from backend import detector
from backend.media import sample_video
from sklearn.metrics import (
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("--kind", choices=["video", "audio"], required=True)
    a = p.parse_args()
    rows = json.loads(a.manifest.read_text(encoding="utf-8"))
    truth = []
    scores = []
    failures = []
    seen = set()
    for row in rows:
        if row["group"] in seen:
            raise ValueError("评测每个原始素材组仅取一个样本，避免重复素材夸大结果")
        seen.add(row["group"])
        if row["label"] not in ("real", "fake"):
            raise ValueError("label必须为real或fake")
        path = bootstrap.ROOT / row["path"]
        try:
            if a.kind == "video":
                _, frames = sample_video(path, 16)
                images = [im for _, im in frames]
                while len(images) < 16:
                    images.append(images[-1])
                result = detector.classify("video", images)
                score = result["score"]
            else:
                with tempfile.TemporaryDirectory() as tmp:
                    values = detector.audio_samples(path, tmp)
                score = detector.classify("audio", values[:160000])["score"]
            truth.append(int(row["label"] == "fake"))
            scores.append(score)
        except Exception as e:
            failures.append({"path": row["path"], "error": str(e)})
    if set(truth) != {0, 1}:
        raise ValueError("成功检测样本必须含真假两类")
    pred = [int(x >= 0.5) for x in scores]
    tn, fp, fn, tp = confusion_matrix(truth, pred, labels=[0, 1]).ravel()
    precision, recall, f1, _ = precision_recall_fscore_support(
        truth, pred, average="binary", zero_division=0
    )
    output = {
        "manifest": str(a.manifest),
        "kind": a.kind,
        "n": len(truth),
        "failures": failures,
        "threshold": 0.5,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "fpr": float(fp / (tn + fp)),
        "fnr": float(fn / (tp + fn)),
        "auc": float(roc_auc_score(truth, scores)),
        "note": "只适用于所列测试样本；评测集必须独立于训练来源",
    }
    directory = bootstrap.ROOT / "reports"
    directory.mkdir(exist_ok=True)
    (directory / (a.kind + "-evaluation.json")).write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(output)


if __name__ == "__main__":
    main()
