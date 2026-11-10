import requests, zipfile, io, json
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def main():
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=Retry(total=6, backoff_factor=1)))
    r = session.get(
        "https://api.github.com/repos/grip-unina/TruFor/commits/main", timeout=30
    )
    r.raise_for_status()
    rev = r.json()["sha"]
    r = session.get(
        f"https://codeload.github.com/grip-unina/TruFor/zip/{rev}", timeout=120
    )
    r.raise_for_status()
    root = (Path(__file__).resolve().parent / "vendor").resolve()
    root.mkdir(exist_ok=True)
    archive = zipfile.ZipFile(io.BytesIO(r.content))
    for item in archive.infolist():
        if not (root / item.filename).resolve().is_relative_to(root):
            raise ValueError("unsafe archive path")
    archive.extractall(root)
    (root / "trufor-source.json").write_text(
        json.dumps(
            {
                "repo": "https://github.com/grip-unina/TruFor",
                "revision": rev,
                "folder": "TruFor-" + rev,
            },
            indent=2,
        )
    )
    print("source ready", rev, flush=True)


if __name__ == "__main__":
    main()
