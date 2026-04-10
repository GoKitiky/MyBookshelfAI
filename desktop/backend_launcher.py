"""Desktop backend launcher entrypoint for the Tauri sidecar binary."""

from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path

import uvicorn

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from app.services.runtime_paths import DATA_DIR_ENV

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8315
DEFAULT_LOG_LEVEL = "info"


def parse_args() -> argparse.Namespace:
    """Parse sidecar launch parameters."""
    parser = argparse.ArgumentParser(description="MyBookshelfAI desktop backend")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--log-level", default=DEFAULT_LOG_LEVEL)
    parser.add_argument("--data-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.data_dir is not None:
        os.environ[DATA_DIR_ENV] = str(args.data_dir.expanduser())

    config = uvicorn.Config(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=False,
    )
    server = uvicorn.Server(config=config)

    def _handle_shutdown(_signum: int, _frame: object | None) -> None:
        server.should_exit = True

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)
    server.run()


if __name__ == "__main__":
    main()
