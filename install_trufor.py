"""Download original inference sources and original author-verified weights."""

import requests, json, hashlib, zipfile, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import bootstrap


def main():
    session = requests.Session()
    session.mount(
        "https://",
        HTTPAdapter(max_retries=Retry(total=5, backoff_factor=1), pool_maxsize=40),
    )
    base = "https://api.github.com/repos/grip-unina/TruFor"
    r = session.get(base + "/commits/main", timeout=30)
    r.raise_for_status()
    rev = r.json()["sha"]
    r = session.get(base + f"/git/trees/{rev}?recursive=1", timeout=30)
    r.raise_for_status()
    entries = [
        e
        for e in r.json()["tree"]
        if e["type"] == "blob"
        and (
            e["path"].startswith("TruFor_train_test/")
            and e["path"].endswith((".py", ".yaml", ".yml", ".txt"))
            or e["path"].lower().startswith("license")
            or e["path"] == "README.md"
        )
    ]
    root = bootstrap.ROOT / "vendor/TruFor"

    def source(e):
        path = root / e["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if e.get("size") == 0:
            path.write_bytes(b"")
            return
        if (
            path.exists()
            and hashlib.sha1(
                b"blob " + str(path.stat().st_size).encode() + b"\0" + path.read_bytes()
            ).hexdigest()
            == e["sha"]
        ):
            return
        r = session.get(
            f"https://raw.githubusercontent.com/grip-unina/TruFor/{rev}/{e['path']}",
            timeout=30,
        )
        r.raise_for_status()
        path.write_bytes(r.content)

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(source, entries))
    (root / "SOURCE.json").write_text(
        json.dumps({"repo": "grip-unina/TruFor", "revision": rev}, indent=2)
    )
    print("sources ready", rev, flush=True)
    target = bootstrap.ROOT / "models/tamper"
    target.mkdir(parents=True, exist_ok=True)
    url = "https://www.grip.unina.it/download/prog/TruFor/TruFor_weights.zip"
    total = 260878690
    step = 4 * 1024 * 1024
    chunks = target / "chunks"
    chunks.mkdir(exist_ok=True)

    def piece(start):
        end = min(total - 1, start + step - 1)
        path = chunks / str(start)
        if path.exists() and path.stat().st_size == end - start + 1:
            return
        r = session.get(
            url, headers={"Range": f"bytes={start}-{end}"}, timeout=(20, 60)
        )
        r.raise_for_status()
        if r.status_code != 206 or len(r.content) != end - start + 1:
            raise ValueError("Range mismatch")
        path.write_bytes(r.content)
        print("TruFor", start, flush=True)

    starts = list(range(0, total, step))
    with ThreadPoolExecutor(max_workers=24) as pool:
        list(pool.map(piece, starts))
    archive = target / "weights.zip"
    with archive.open("wb") as out:
        for start in starts:
            out.write((chunks / str(start)).read_bytes())
    if (
        hashlib.md5(archive.read_bytes()).hexdigest()
        != "7bee48f3476c75616c3c5721ab256ff8"
    ):
        raise ValueError("Author MD5 mismatch")
    z = zipfile.ZipFile(archive)
    member = next(n for n in z.namelist() if n.endswith((".pth.tar", ".pth")))
    (target / "trufor.pth.tar").write_bytes(z.read(member))
    (target / "source.json").write_text(
        json.dumps(
            {
                "repo": "grip-unina/TruFor",
                "revision": rev,
                "license": "author nonprofit research license; see vendor/TruFor/TruFor_train_test/LICENSE.txt",
                "archive_md5": "7bee48f3476c75616c3c5721ab256ff8",
            },
            indent=2,
        )
    )
    print("TruFor ready", flush=True)


if __name__ == "__main__":
    main()
