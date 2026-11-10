"""Exercise real model weights. Engineering smoke results are not benchmark accuracy."""

import bootstrap
import json, tempfile
import cv2, numpy as np
from backend import detector
from backend.media import sample_video


def main():
    results = {
        "purpose": "engineering verification only; not independent accuracy benchmark",
        "models": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        from pathlib import Path

        path = Path(tmp) / "test.avi"
        writer = cv2.VideoWriter(
            str(path), cv2.VideoWriter_fourcc(*"MJPG"), 8, (224, 224)
        )
        for n in range(24):
            frame = np.zeros((224, 224, 3), dtype=np.uint8)
            cv2.circle(frame, (30 + n * 5, 100), 20, (80, 160, 220), -1)
            writer.write(frame)
        writer.release()
        _, frames = sample_video(path, 16)
        results["models"]["video"] = detector.classify(
            "video", [im for _, im in frames]
        )
        samples = json.loads((bootstrap.ROOT / "data/sample-source.json").read_text())
        results["audio_samples"] = []
        for row in samples["records"]:
            values = detector.audio_samples(bootstrap.ROOT / row["path"], tmp)
            result = detector.classify("audio", values[:160000])
            result.update(label=row["label"], path=row["path"])
            results["audio_samples"].append(result)
            (Path(tmp) / "audio.wav").unlink()
    root = bootstrap.ROOT / "reports"
    root.mkdir(exist_ok=True)
    (root / "model-smoke.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
