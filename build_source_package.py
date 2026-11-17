"""Package the current TruthLens source and verify the resulting ZIP."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


ROOT = Path(__file__).resolve().parent
SOURCE_DIRS = ("backend", "web", "frontend", "frontend-next", "vendor", "docs", "release")
LOCAL_DIRS = {"node_modules", "__pycache__", ".git", ".idea", ".venv", "runtime", ".packages"}
EXCLUDED_VENDOR_DIRS = (
    ("vendor", "TruFor", "TruFor_train_test", "dataset", "data"),
    ("vendor", "OSTF", "mmdet", ".mim", "demo"),
)
PRIVATE_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".key", ".pem", ".pfx", ".log", ".part", ".zip", ".7z", ".rar"}
IGNORED_SUFFIXES = PRIVATE_SUFFIXES | {".pyc", ".pyo", ".tsbuildinfo", ".mp4", ".safetensors", ".pth", ".onnx", ".ckpt", ".tar"}
ROOT_FILES = {".gitignore", ".gitattributes", ".env.example", "README.md", "team.json"}
MODEL_FILES = (
    "models/active-audio.json",
    "models/active-domain.json",
    "models/active-video.json",
    "models/provided-image-head/best-head.pt",
    "models/provided-image-head/community-epoch20-head.pt",
    "models/community/config.json",
    "models/community/source.json",
    "models/truthlens-ast-qwen/config.json",
    "models/truthlens-ast-qwen/ast_adapted.npz",
    "models/text-patterns/config.json",
    "models/text-patterns/weights.npz",
    "models/chat-ocr/source.json",
    "models/asr_zh/source.json",
    "models/asr_zh/tokens.txt",
    "models/face-detector/model.onnx",
    "models/face-detector/source.json",
    "models/gend-clip/source.json",
    "models/verispoof/NOTICE",
    "models/verispoof/LICENSE-Apache-2.0.txt",
)
RUNTIME_ASSETS = (
    ("runtime/ocr-packages", "runtime/ocr-packages"),
    ("runtime/forensics-pilot/daf-torch", "runtime/forensics-pilot/daf-torch"),
    ("runtime/forensics-pilot/daf-helpers", "runtime/forensics-pilot/daf-helpers"),
    ("runtime/verification-download-cache/smaug-packages", "runtime/smaug-packages"),
    (".packages", ".packages"),
    (".agent-packages", ".agent-packages"),
)
FULL_REQUIRED = {
    "models/community/model.safetensors",
    "models/fused/fused_opensdi.pth",
    "models/fused/convnext.safetensors",
    "models/daf/srnet-tensors.pt",
    "models/truthlens-ast-qwen/model.safetensors",
    "models/truthlens-ast-qwen/ast_adapted.npz",
    "models/gend-clip/model.safetensors",
    "models/asr_zh/model.int8.onnx",
    "models/advisor/model.safetensors",
    "models/text-patterns/weights.npz",
    "runtime/ocr-packages/rapidocr/models/PP-OCRv6_det_small.onnx",
    "runtime/ocr-packages/rapidocr/models/PP-OCRv6_rec_small.onnx",
    "runtime/ocr-packages/rapidocr/models/ch_ppocr_mobile_v2.0_cls_mobile.onnx",
    "runtime/forensics-pilot/daf-torch/torch/__init__.py",
    "runtime/forensics-pilot/daf-helpers/mmcv/__init__.py",
    "vendor/FUSED/fused/model/model.py",
    "vendor/OSTF/configs/fasterrcnn_xsrnet.py",
}
RUNTIME_PREFIXES = tuple(Path(destination).parts for _, destination in RUNTIME_ASSETS if destination.startswith("runtime/"))


def private_file(path):
    return (path.suffix.lower() in PRIVATE_SUFFIXES and path.parts[-2:] != ("certifi", "cacert.pem")
            or ".sqlite" in path.name.lower()
            or path.name.lower().startswith(("credentials", "admin-setup", "companion-model")))


def excluded(path):
    return (
        bool(LOCAL_DIRS.intersection(path.parts))
        or any(path.parts[:len(folder)] == folder for folder in EXCLUDED_VENDOR_DIRS)
        or path.suffix.lower() in IGNORED_SUFFIXES
        or path.name.lower().startswith((".env", "admin-setup", "companion-model", "credentials"))
        or (path.suffix.lower() == ".pt" and path.parts[0] != "release")
    )


def source_files():
    for path in ROOT.iterdir():
        if path.is_file() and (path.name in ROOT_FILES or path.suffix.lower() in {".py", ".ps1", ".cmd", ".txt"}):
            if not path.is_symlink() and (path.name == ".env.example" or not excluded(path.relative_to(ROOT))):
                yield path
    for folder in SOURCE_DIRS:
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and not path.is_symlink() and not excluded(path.relative_to(ROOT)):
                yield path
    for path in (ROOT / "data/demo").iterdir():
        if not path.is_symlink() and path.is_file() and path.suffix in {".json", ".mp3"}:
            yield path
    for name in MODEL_FILES:
        path = ROOT / name
        if path.is_file():
            yield path


def full_assets():
    roots = (("models", "models"), *RUNTIME_ASSETS)
    ignored_dirs = {"__pycache__", ".git", "chunks", "cache", ".cache"}
    for source, destination in roots:
        root = ROOT / source
        for directory, folders, filenames in os.walk(root):
            here = Path(directory)
            folders[:] = [
                name for name in folders
                if name not in ignored_dirs and not (here / name).is_symlink()
            ]
            for name in filenames:
                path = here / name
                if (path.is_symlink() or private_file(path) or path.suffix.lower() in {".pyc", ".pyo", ".whl"}
                        or name.lower().startswith(".env")):
                    continue
                yield path, (Path(destination) / path.relative_to(root)).as_posix()
    for path in (ROOT / "data/demo").glob("*.mp4"):
        if path.is_file() and not path.is_symlink():
            yield path, path.relative_to(ROOT).as_posix()


def check_archive(path, *, full=False):
    with ZipFile(path) as archive:
        names = set(archive.namelist())
        required = {
            "qinan/README.md", "qinan/setup.ps1", "qinan/start.cmd", "qinan/run.py",
            "qinan/frontend-next/index.html", "qinan/backend/admin_api.py",
            "qinan/backend/verification_cases.json", "qinan/web/src/views/Admin.tsx",
            "qinan/web/src/admin.css", "qinan/web/package-lock.json",
            "qinan/release/ordered-video-head.pt", "qinan/models/active-domain.json",
            "qinan/models/active-video.json", "qinan/models/active-audio.json",
        }
        if full:
            required |= {"qinan/" + name for name in FULL_REQUIRED}
        if required - names:
            raise ValueError("Missing archive entries: " + ", ".join(sorted(required - names)))
        if len(names) != len(archive.infolist()):
            raise ValueError("Duplicate archive paths")
        for name in names:
            relative = Path(name).relative_to("qinan")
            if private_file(relative):
                raise ValueError("Archive contains private runtime data: " + name)
            if "runtime" in relative.parts and not (
                full and any(relative.parts[:len(prefix)] == prefix for prefix in RUNTIME_PREFIXES)
            ):
                raise ValueError("Archive contains a non-packaged runtime path: " + name)
        print(f"Checking ZIP integrity ({len(names):,} entries)", flush=True)
        bad_file = archive.testzip()
        if bad_file:
            raise ValueError("ZIP integrity check failed: " + bad_file)
        return len(names)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?", default=ROOT / "submission/TruthLens_参赛源码包.zip")
    parser.add_argument("--full", action="store_true", help="include local model weights and inference libraries")
    args = parser.parse_args()
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    public = json.loads((ROOT / "docs/benchmarks.json").read_text(encoding="utf-8"))["reports"]
    with NamedTemporaryFile(dir=target.parent, suffix=".zip.tmp", delete=False) as temporary:
        pending = Path(temporary.name)
    try:
        assets = {path.relative_to(ROOT).as_posix(): path for path in source_files()}
        if args.full:
            assets.update((relative, path) for path, relative in full_assets())
        with ZipFile(pending, "w", compression=ZIP_DEFLATED, compresslevel=1) as archive:
            for index, (relative, path) in enumerate(sorted(assets.items()), start=1):
                size = path.stat().st_size
                if size >= 64 * 1024 * 1024:
                    print(f"Adding {relative} ({size / 1024**2:.0f} MiB)", flush=True)
                stored = size >= 64 * 1024 * 1024 and path.suffix.lower() in {".safetensors", ".pth", ".pt", ".onnx", ".tar"}
                archive.write(path, "qinan/" + relative, compress_type=ZIP_STORED if stored else ZIP_DEFLATED)
                if index % 5000 == 0:
                    print(f"Archived {index:,} of {len(assets):,} files", flush=True)
            for name, value in sorted(public.items()):
                archive.writestr("qinan/reports/" + name, json.dumps(value, ensure_ascii=False, indent=2))
        files = check_archive(pending, full=args.full)
        pending.replace(target)
    finally:
        pending.unlink(missing_ok=True)
    checksum = hashlib.sha256()
    with target.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            checksum.update(block)
    print(json.dumps({"file": str(target), "bytes": target.stat().st_size, "files": files,
                      "sha256": checksum.hexdigest()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
