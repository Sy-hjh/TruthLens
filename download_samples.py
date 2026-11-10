"""Small source-overlapping audio set for engineering checks, NOT an independent benchmark."""

import requests, json
import bootstrap


def main():
    repo = "garystafford/deepfake-audio-detection"
    base = "https://huggingface.co"
    meta = requests.get(f"{base}/api/datasets/{repo}", timeout=30)
    meta.raise_for_status()
    revision = meta.json()["sha"]
    records = []
    for label in ("real", "fake"):
        response = requests.get(
            f"{base}/api/datasets/{repo}/tree/{revision}/{label}", timeout=30
        )
        response.raise_for_status()
        files = [
            x
            for x in response.json()
            if x["type"] == "file" and x["path"].endswith((".flac", ".wav", ".mp3"))
        ][:3]
        for item in files:
            path = bootstrap.ROOT / "data" / "smoke" / item["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                r = requests.get(
                    f"{base}/datasets/{repo}/resolve/{revision}/{item['path']}",
                    timeout=60,
                )
                r.raise_for_status()
                path.write_bytes(r.content)
            records.append(
                {
                    "path": path.relative_to(bootstrap.ROOT).as_posix(),
                    "label": label,
                    "bytes": path.stat().st_size,
                }
            )
    (bootstrap.ROOT / "data" / "sample-source.json").write_text(
        json.dumps(
            {
                "repo": repo,
                "revision": revision,
                "license": meta.json().get("cardData", {}).get("license"),
                "purpose": "source-overlapping engineering smoke test only",
                "records": records,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(records)


if __name__ == "__main__":
    main()
