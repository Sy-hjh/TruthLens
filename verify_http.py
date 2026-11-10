import bootstrap, json, time, tempfile, sys, subprocess
from pathlib import Path
import cv2, numpy as np
from fastapi.testclient import TestClient
from backend.app import app


def main():
    client = TestClient(app)
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        video = Path(tmp) / "qa.avi"
        writer = cv2.VideoWriter(
            str(video), cv2.VideoWriter_fourcc(*"MJPG"), 8, (224, 224)
        )
        for n in range(24):
            frame = np.zeros((224, 224, 3), np.uint8)
            cv2.circle(frame, (30 + n * 4, 100), 20, (20, 160, 220), -1)
            writer.write(frame)
        writer.release()
        audio = next((bootstrap.ROOT / "data/smoke/real").glob("*.flac"))
        import imageio_ffmpeg

        av = Path(tmp) / "qa-with-audio.mp4"
        subprocess.run(
            [
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(video),
                "-i",
                str(audio),
                "-shortest",
                "-c:v",
                "mpeg4",
                "-c:a",
                "aac",
                str(av),
            ],
            check=True,
            timeout=60,
        )
        inputs = [video, av, audio]
        if "--video-only" in sys.argv:
            inputs = [video]
        for path in inputs:
            with path.open("rb") as f:
                r = client.post(
                    "/api/analyze",
                    files={"file": (path.name, f)},
                    data={"context": "测试材料：有人要求马上转账，不要告诉家人"},
                )
            assert r.status_code == 202, r.text
            job_id = r.json()["job_id"]
            for _ in range(240):
                job = client.get("/api/jobs/" + job_id).json()
                if job["status"] != "processing":
                    break
                time.sleep(0.5)
            assert job["status"] == "completed", job
            result = job["result"]
            expected = "audio" if path == audio else "video"
            if expected=='video' and result['modules'][expected]['status']!='completed':
                assert '人脸' in result['modules'][expected].get('note',''),result
            else:assert result['modules'][expected]['status']=='completed',result
            if path == av:
                assert result["modules"]["audio"]["status"] == "completed", result
            assert client.get("/api/cases/" + job_id).status_code == 200
            results.append(
                {
                    "input": path.name,
                    "modules": {k: v["status"] for k, v in result["modules"].items()},
                    "transcript_status": result.get("transcript", {}).get("status"),
                }
            )
            client.delete("/api/cases/" + job_id)
            assert client.get("/api/cases/" + job_id).status_code == 404
    target = bootstrap.ROOT / (
        "reports/video-http-qa.json"
        if "--video-only" in sys.argv
        else "reports/http-qa.json"
    )
    target.parent.mkdir(exist_ok=True)
    target.write_text(
        json.dumps({"purpose": "engineering only", "results": results}, indent=2),
        encoding="utf-8",
    )
    print(results)


if __name__ == "__main__":
    main()
