import requests, json, time, hashlib
import bootstrap
from concurrent.futures import ThreadPoolExecutor

MODELS = {
    "community": "OwensLab/commfor-model-224",
    "video": "Vansh180/VideoMae-ffc23-deepfake-detector",
    "audio": "garystafford/wav2vec2-deepfake-voice-detector",
    "asr": "openai/whisper-tiny",
    "asr_small": "openai/whisper-small",
    "image": "Ateeqq/ai-vs-human-image-detector",
    "asr_zh": "csukuangfj/sherpa-onnx-paraformer-zh-2024-03-09",
}

# Reproduce the validated release rather than silently following future main.
REVISIONS = {
    "community": "26afc31e6b40c312c3fd42c05a758be62446215b",
    "video": "ea26518b527d938d66e568c52bcf1c19a86cf295",
    "audio": "c66306024a7ede0be291e9c4558b37634782dc4e",
    "asr": "169d4a4341b33bc18d8881c4b69c2e104e1cc0af",
    "asr_small": "973afd24965f72e36ca33b3055d56a652f456b4d",
    "image": "60e82406916921b823616bee33397baab38af3f0",
    "asr_zh": "906992d326ebf0c5171cde675aa0902be9e5bc6c",
}


def main():
    import sys
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    session.mount(
        "https://",
        HTTPAdapter(max_retries=Retry(total=5, backoff_factor=1), pool_maxsize=40),
    )
    requests.get = session.get
    for kind, repo in MODELS.items():
        if len(sys.argv) > 1 and kind != sys.argv[1]:
            continue
        r = requests.get(
            f"https://huggingface.co/api/models/{repo}/revision/{REVISIONS[kind]}?blobs=true", timeout=30
        )
        r.raise_for_status()
        meta = r.json()
        rev = meta["sha"]
        root = bootstrap.ROOT / "models" / kind
        root.mkdir(parents=True, exist_ok=True)
        names = [
            x["rfilename"]
            for x in meta["siblings"]
            if x["rfilename"]
            in (
                "config.json",
                "preprocessor_config.json",
                "model.safetensors",
                "README.md",
                "LICENSE",
            )
        ]
        if kind == "asr_zh":
            names = [
                x["rfilename"]
                for x in meta["siblings"]
                if x["rfilename"]
                in ("model.int8.onnx", "tokens.txt", "README.md", "LICENSE")
            ]
        elif kind.startswith("asr"):
            names = [
                x["rfilename"]
                for x in meta["siblings"]
                if "/" not in x["rfilename"]
                and (
                    x["rfilename"].endswith(".json")
                    or x["rfilename"]
                    in ("model.safetensors", "merges.txt", "README.md", "LICENSE")
                )
            ]

        def fetch(name):
            path = root / name
            if path.exists():
                return
            if name.endswith((".safetensors", ".onnx")):
                url = f"https://huggingface.co/{repo}/resolve/{rev}/{name}"
                with requests.get(
                    url, headers={"Range": "bytes=0-0"}, timeout=(30, 45)
                ) as head:
                    head.raise_for_status()
                    total = int(head.headers["Content-Range"].split("/")[-1])
                chunks = root / "chunks"
                chunks.mkdir(exist_ok=True)
                step = 4 * 1024 * 1024

                def piece(start):
                    end = min(total - 1, start + step - 1)
                    part = chunks / str(start)
                    if part.exists() and part.stat().st_size == end - start + 1:
                        return
                    for retry in range(8):
                        try:
                            r = requests.get(
                                url,
                                headers={"Range": f"bytes={start}-{end}"},
                                timeout=(20, 60),
                            )
                            r.raise_for_status()
                            if (
                                r.status_code != 206
                                or len(r.content) != end - start + 1
                            ):
                                raise ValueError("range mismatch")
                            part.write_bytes(r.content)
                            print(kind, "chunk", start, "/", total, flush=True)
                            return
                        except Exception:
                            if retry == 7:
                                raise

                starts = list(range(0, total, step))
                with ThreadPoolExecutor(max_workers=32) as workers:
                    list(workers.map(piece, starts))
                with path.with_suffix(".part").open("wb") as dest:
                    for start in starts:
                        dest.write((chunks / str(start)).read_bytes())
                path.with_suffix(".part").replace(path)
                print(kind, name, total, flush=True)
                return
            temp = path.with_suffix(".part")
            for attempt in range(20):
                offset = temp.stat().st_size if temp.exists() else 0
                try:
                    with requests.get(
                        f"https://huggingface.co/{repo}/resolve/{rev}/{name}",
                        headers={"Range": f"bytes={offset}-"} if offset else {},
                        stream=True,
                        timeout=(30, 180),
                    ) as response:
                        response.raise_for_status()
                        mode = "ab" if offset and response.status_code == 206 else "wb"
                        with temp.open(mode) as f:
                            for chunk in response.iter_content(1024 * 1024):
                                f.write(chunk)
                    break
                except requests.RequestException:
                    if attempt == 19:
                        raise
                    print("retry", kind, name, attempt + 1, flush=True)
                    time.sleep(1)
            path.with_suffix(".part").replace(path)
            print(kind, name, path.stat().st_size, flush=True)

        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(fetch, names))
        for entry in meta["siblings"]:
            if entry["rfilename"] in names and entry.get("lfs", {}).get("sha256"):
                actual = hashlib.sha256(
                    (root / entry["rfilename"]).read_bytes()
                ).hexdigest()
                if actual != entry["lfs"]["sha256"]:
                    raise ValueError("模型SHA256不匹配，不能启用")
        hashes = {
            e["rfilename"]: e["lfs"]["sha256"]
            for e in meta["siblings"]
            if e["rfilename"] in names and e.get("lfs", {}).get("sha256")
        }
        (root / "source.json").write_text(
            json.dumps(
                {
                    "repo": repo,
                    "revision": rev,
                    "license": meta.get("cardData", {}).get("license"),
                    "files": names,
                    "verified_sha256": hashes,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
