import requests, hashlib, zipfile
from concurrent.futures import ThreadPoolExecutor
import bootstrap


def main():
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=Retry(total=5, backoff_factor=1)))
    requests.get = session.get
    info = requests.get("https://pypi.org/pypi/imageio-ffmpeg/json", timeout=20)
    info.raise_for_status()
    file = next(x for x in info.json()["urls"] if "win_amd64" in x["filename"])
    step = 4 * 1024 * 1024
    root = bootstrap.ROOT / "runtime" / "ffmpeg-download"
    root.mkdir(exist_ok=True)

    def piece(start):
        end = min(file["size"] - 1, start + step - 1)
        path = root / str(start)
        if path.exists() and path.stat().st_size == end - start + 1:
            return
        r = requests.get(
            file["url"], headers={"Range": f"bytes={start}-{end}"}, timeout=60
        )
        r.raise_for_status()
        if len(r.content) != end - start + 1:
            raise ValueError("download length mismatch")
        path.write_bytes(r.content)
        print("ffmpeg", start, flush=True)

    starts = list(range(0, file["size"], step))
    with ThreadPoolExecutor(max_workers=6) as workers:
        list(workers.map(piece, starts))
    wheel = root / file["filename"]
    with wheel.open("wb") as dest:
        for start in starts:
            dest.write((root / str(start)).read_bytes())
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != file["digests"]["sha256"]:
        raise ValueError("wheel digest mismatch")
    zipfile.ZipFile(wheel).extractall(bootstrap.ROOT / ".packages")
    print("ffmpeg installed")


if __name__ == "__main__":
    main()
