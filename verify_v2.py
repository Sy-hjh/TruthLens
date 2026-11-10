"""Real-weight functional checks, regression evidence and malformed input boundaries."""

import bootstrap, json, tempfile, time, wave, hashlib, sqlite3
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import numpy as np, cv2
from fastapi.testclient import TestClient
from backend import storage
from backend.app import app


def main():
    checks = []
    regressions = []
    with tempfile.TemporaryDirectory() as directory, patch.object(
        storage, "ROOT", Path(directory)
    ):
        client = TestClient(app)

        def submit(path, expected=None):
            with Path(path).open("rb") as f:
                r = client.post("/api/analyze", files={"file": (Path(path).name, f)})
            assert r.status_code == 202, r.text
            key = r.json()["job_id"]
            start = time.monotonic()
            for _ in range(600):
                job = client.get("/api/jobs/" + key).json()
                if job["status"] != "processing":
                    break
                time.sleep(0.25)
            if expected:
                assert job["status"] == "completed", job
                for name in expected:
                    assert job["result"]["modules"][name]["status"] == "completed", job
            checks.append(
                {
                    "file": Path(path).name,
                    "status": job["status"],
                    "seconds": round(time.monotonic() - start, 2),
                    "asr": job.get("result", {})
                    .get("transcript", {})
                    .get("source", {})
                    .get("repo"),
                    "modules": {
                        k: v["status"]
                        for k, v in job.get("result", {}).get("modules", {}).items()
                    },
                }
            )
            return job

        for name in (
            "family-simulation",
            "expert-simulation",
            "normal-synthetic-control",
        ):
            job = submit(bootstrap.ROOT / "data/demo" / (name + ".mp3"), ["audio"])
            assert job["result"]["transcript"]["status"] == "completed"
            if name == "normal-synthetic-control":
                assert not job["result"]["phrases"], job["result"]["phrases"]
            else:
                assert job["result"]["phrases"], "模拟风险表达没有被提取"
        for suffix in (".jpg", ".png"):
            path = Path(directory) / ("synthetic-color" + suffix)
            Image.new("RGB", (256, 256), (100, 150, 80)).save(path)
            job = submit(path, ["image", "tamper"])
            assert job["result"]["modules"]["tamper"]["map_png"].startswith(
                "data:image/png;base64,"
            )
        malformed = Path(directory) / "broken.png"
        malformed.write_bytes(b"not-an-image")
        assert submit(malformed)["status"] == "failed"
        silent = Path(directory) / "silent.wav"
        with wave.open(str(silent), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(np.zeros(32000, dtype=np.int16).tobytes())
        job = submit(silent)
        assert job["result"]["modules"]["audio"]["status"] == "failed"
        long_video = Path(directory) / "too-long.avi"
        out = cv2.VideoWriter(
            str(long_video), cv2.VideoWriter_fourcc(*"MJPG"), 1, (64, 64)
        )
        for _ in range(181):
            out.write(np.zeros((64, 64, 3), np.uint8))
        out.release()
        assert submit(long_video)["status"] == "failed"
        assert not any(
            p.name.startswith("tmp") and p.is_dir() for p in Path(directory).iterdir()
        ), "上传临时目录没有清理"
        for item in client.get("/api/cases").json():
            client.delete("/api/cases/" + item["id"])
            assert client.get("/api/cases/" + item["id"]).status_code == 404
    target = bootstrap.ROOT / "reports/v2-functional.json"
    target.write_text(
        json.dumps(
            {
                "checks": checks,
                "note": "functional assertions; synthetic-color image is not an accuracy benchmark",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
