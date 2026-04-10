"""Build the Linux backend sidecar binary for Tauri packaging."""

from __future__ import annotations

import argparse
import shutil
import stat
import subprocess
import sys
from pathlib import Path

DEFAULT_TARGET_TRIPLE = "x86_64-unknown-linux-gnu"
SIDE_CAR_NAME = "mybookshelf-backend"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build backend sidecar binary with PyInstaller"
    )
    parser.add_argument(
        "--python",
        default=None,
        help="Python interpreter used to run PyInstaller",
    )
    parser.add_argument(
        "--target-triple",
        default=None,
        help="Rust target triple suffix used by Tauri sidecars",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete previous build artifacts before building",
    )
    return parser.parse_args()


def _detect_target_triple() -> str:
    try:
        out = subprocess.run(
            ["rustc", "-vV"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return DEFAULT_TARGET_TRIPLE

    for line in out.splitlines():
        if line.startswith("host: "):
            host = line.split("host: ", 1)[1].strip()
            if host:
                return host
    return DEFAULT_TARGET_TRIPLE


def _resolve_python(root_dir: Path) -> str:
    preferred = root_dir / ".venv" / "bin" / "python"
    if preferred.exists():
        return str(preferred)

    python3 = shutil.which("python3")
    if python3:
        return python3

    python = shutil.which("python")
    if python:
        return python
    return sys.executable


def _ensure_pyinstaller(python_executable: str) -> None:
    check_cmd = [
        python_executable,
        "-c",
        "import PyInstaller.__main__",  # noqa: S603,S607
    ]
    try:
        subprocess.run(check_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "PyInstaller is not installed for the selected Python. "
            "Install it with: pip install pyinstaller"
        ) from exc


def _run_pyinstaller(
    *,
    root_dir: Path,
    python_executable: str,
    launcher_file: Path,
    build_root: Path,
) -> Path:
    dist_path = build_root / "dist"
    work_path = build_root / "work"
    spec_path = build_root / "spec"
    dist_path.mkdir(parents=True, exist_ok=True)
    work_path.mkdir(parents=True, exist_ok=True)
    spec_path.mkdir(parents=True, exist_ok=True)

    cmd = [
        python_executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        SIDE_CAR_NAME,
        "--distpath",
        str(dist_path),
        "--workpath",
        str(work_path),
        "--specpath",
        str(spec_path),
        "--paths",
        str(root_dir),
        str(launcher_file),
    ]
    subprocess.run(cmd, check=True, cwd=root_dir)
    built_bin = dist_path / SIDE_CAR_NAME
    if not built_bin.exists():
        raise FileNotFoundError(f"PyInstaller output is missing: {built_bin}")
    return built_bin


def _copy_to_tauri_sidecar(
    *,
    built_binary: Path,
    frontend_tauri_dir: Path,
    target_triple: str,
) -> Path:
    binaries_dir = frontend_tauri_dir / "binaries"
    binaries_dir.mkdir(parents=True, exist_ok=True)

    target_name = f"{SIDE_CAR_NAME}-{target_triple}"
    target_path = binaries_dir / target_name
    shutil.copy2(built_binary, target_path)

    mode = target_path.stat().st_mode
    target_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return target_path


def main() -> None:
    args = parse_args()
    root_dir = Path(__file__).resolve().parent.parent
    launcher_file = root_dir / "desktop" / "backend_launcher.py"
    build_root = root_dir / "build" / "desktop-sidecar"
    frontend_tauri_dir = root_dir / "frontend" / "src-tauri"

    python_executable = args.python or _resolve_python(root_dir)

    if args.clean and build_root.exists():
        shutil.rmtree(build_root)

    _ensure_pyinstaller(python_executable)
    built_binary = _run_pyinstaller(
        root_dir=root_dir,
        python_executable=python_executable,
        launcher_file=launcher_file,
        build_root=build_root,
    )
    sidecar_path = _copy_to_tauri_sidecar(
        built_binary=built_binary,
        frontend_tauri_dir=frontend_tauri_dir,
        target_triple=args.target_triple or _detect_target_triple(),
    )
    print(f"Built sidecar: {sidecar_path}")


if __name__ == "__main__":
    main()
