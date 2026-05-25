from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTALL_DIR = REPO_ROOT / ".local" / "tools" / "llama.cpp"
GITHUB_RELEASE_API = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"


def _fetch_json(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response, target.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _pick_asset(release: dict[str, Any], *, contains: list[str], excludes: list[str] | None = None) -> dict[str, Any]:
    assets = release.get("assets") or []
    excludes = excludes or []
    for asset in assets:
        name = str(asset.get("name") or "").lower()
        if all(token.lower() in name for token in contains) and not any(token.lower() in name for token in excludes):
            return asset
    raise RuntimeError(f"No llama.cpp release asset matched {contains!r}")


def _extract(zip_path: Path, install_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(install_dir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install-dir", default=str(DEFAULT_INSTALL_DIR))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--prefer-cuda", default="cuda-12")
    args = parser.parse_args()

    install_dir = Path(args.install_dir).resolve()
    cli = install_dir / "llama-mtmd-cli.exe"
    server = install_dir / "llama-server.exe"
    if cli.exists() and not args.force:
        print(json.dumps({"ok": True, "already_installed": True, "cli": str(cli), "server": str(server)}, ensure_ascii=False))
        return 0

    release = _fetch_json(GITHUB_RELEASE_API)
    tag = release.get("tag_name")
    bin_asset = _pick_asset(release, contains=["llama", "bin", "win", "cuda", "x64"], excludes=["cudart"])
    cudart_asset = _pick_asset(release, contains=["cudart", "win", "cuda", "x64"])

    downloads = install_dir / "_downloads"
    if args.force and install_dir.exists():
        shutil.rmtree(install_dir)
    install_dir.mkdir(parents=True, exist_ok=True)

    for asset in (bin_asset, cudart_asset):
        target = downloads / str(asset["name"])
        _download(str(asset["browser_download_url"]), target)
        _extract(target, install_dir)

    candidates = list(install_dir.rglob("llama-mtmd-cli.exe"))
    if not candidates:
        raise RuntimeError(f"llama-mtmd-cli.exe was not found after extracting assets into {install_dir}")
    for exe in candidates:
        if exe.parent != install_dir:
            shutil.copy2(exe, install_dir / exe.name)
    for exe in install_dir.rglob("llama-server.exe"):
        if exe.parent != install_dir:
            shutil.copy2(exe, install_dir / exe.name)
    for dll in install_dir.rglob("*.dll"):
        if dll.parent != install_dir:
            dest = install_dir / dll.name
            if not dest.exists():
                shutil.copy2(dll, dest)

    print(
        json.dumps(
            {
                "ok": True,
                "tag": tag,
                "install_dir": str(install_dir),
                "cli": str(install_dir / "llama-mtmd-cli.exe"),
                "server": str(install_dir / "llama-server.exe"),
                "assets": [bin_asset.get("name"), cudart_asset.get("name")],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
