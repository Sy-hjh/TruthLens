import requests, json, hashlib
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import bootstrap


def main():
    session = requests.Session()
    session.mount(
        "https://",
        HTTPAdapter(
            max_retries=Retry(
                total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
            )
        ),
    )
    repo = "PolyAI/minds14"
    meta = session.get(f"https://huggingface.co/api/datasets/{repo}", timeout=30)
    meta.raise_for_status()
    root = bootstrap.ROOT / "data/chinese-human"
    root.mkdir(parents=True, exist_ok=True)
    records = []
    revision = meta.json()["sha"]
    listing = session.get(
        f"https://huggingface.co/api/datasets/{repo}/tree/{revision}/zh-CN", timeout=30
    )
    listing.raise_for_status()
    info = listing.json()[0]
    archive = root / "raw.parquet"
    chunks = root / "chunks"
    chunks.mkdir(exist_ok=True)
    step = 4 * 1024 * 1024
    size = info["size"]

    def piece(start):
        end = min(size - 1, start + step - 1)
        path = chunks / str(start)
        if path.exists() and path.stat().st_size == end - start + 1:
            return
        r = session.get(
            f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{info['path']}",
            headers={"Range": f"bytes={start}-{end}"},
            timeout=60,
        )
        r.raise_for_status()
        if len(r.content) != end - start + 1:
            raise ValueError("range length mismatch")
        path.write_bytes(r.content)

    starts = list(range(0, size, step))
    if not archive.exists():
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(piece, starts))
        with archive.open("wb") as out:
            for start in starts:
                out.write((chunks / str(start)).read_bytes())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != info["lfs"]["oid"]:
        raise ValueError("dataset SHA256 mismatch")
    import pyarrow.parquet as pq

    for index, row in enumerate(pq.read_table(archive).slice(0, 6).to_pylist()):
        path = root / (str(index) + ".wav")
        path.write_bytes(row["audio"]["bytes"])
        records.append(
            {
                "path": path.relative_to(bootstrap.ROOT).as_posix(),
                "label": "real",
                "transcription": row["transcription"],
                "row_idx": index,
                "bytes": path.stat().st_size,
            }
        )
    (root / "source.json").write_text(
        json.dumps(
            {
                "repo": repo,
                "revision": meta.json()["sha"],
                "license": meta.json().get("cardData", {}).get("license"),
                "purpose": "small Chinese telephone-speech pilot; no elderly or speaker-independent claim",
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("downloaded", len(records), "Chinese human audio files")


if __name__ == "__main__":
    main()
