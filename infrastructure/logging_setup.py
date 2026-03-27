"""Rotating file logging under project ``logs/`` only."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(*, log_dir: Path, app_name: str = "humanos") -> None:
    """
    Configure root logger: console + ``app.log`` (INFO+) + ``error.log`` (ERROR+).

    Files are created only under ``log_dir`` (must be inside project).
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    app_log = log_dir / "app.log"
    err_log = log_dir / "error.log"

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Avoid duplicate handlers on reload
    if root.handlers:
        for h in list(root.handlers):
            root.removeHandler(h)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    app_handler = RotatingFileHandler(
        app_log,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(fmt)
    root.addHandler(app_handler)

    err_handler = RotatingFileHandler(
        err_log,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(fmt)
    root.addHandler(err_handler)

    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.info("Logging initialized (%s)", app_name)
