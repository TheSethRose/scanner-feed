import gzip
import shutil
import time
from pathlib import Path

from .config import (
    COMPRESS_OLD_CSV_DAYS,
    CSV_MAX_TOTAL_MB,
    CSV_RETENTION_DAYS,
    KEEP_SEGMENTS,
    LOG_DIR,
    SEGMENT_RETENTION_MINUTES,
    WORKDIR,
    debug,
)


def cleanup_old_segments() -> None:
    if KEEP_SEGMENTS:
        return

    cutoff = time.time() - SEGMENT_RETENTION_MINUTES * 60

    for path in WORKDIR.glob("*.wav"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                debug(f"deleted orphaned segment {path}")
        except FileNotFoundError:
            continue


def compress_old_csvs() -> None:
    if COMPRESS_OLD_CSV_DAYS < 0:
        return

    cutoff = time.time() - COMPRESS_OLD_CSV_DAYS * 86400

    for path in LOG_DIR.glob("scanner-events-*.csv"):
        try:
            if path.stat().st_mtime >= cutoff:
                continue

            gz_path = path.with_suffix(path.suffix + ".gz")

            if gz_path.exists():
                path.unlink()
                continue

            with path.open("rb") as source, gzip.open(gz_path, "wb") as target:
                shutil.copyfileobj(source, target)

            path.unlink()
        except FileNotFoundError:
            continue


def prune_old_csvs() -> None:
    if CSV_RETENTION_DAYS < 0:
        return

    cutoff = time.time() - CSV_RETENTION_DAYS * 86400

    for path in list(LOG_DIR.glob("scanner-events-*.csv")) + list(LOG_DIR.glob("scanner-events-*.csv.gz")):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except FileNotFoundError:
            continue


def enforce_csv_size_limit() -> None:
    if CSV_MAX_TOTAL_MB <= 0:
        return

    paths = sorted(
        list(LOG_DIR.glob("scanner-events-*.csv")) + list(LOG_DIR.glob("scanner-events-*.csv.gz")),
        key=lambda path: path.stat().st_mtime if path.exists() else 0,
    )
    max_bytes = int(CSV_MAX_TOTAL_MB * 1024 * 1024)

    def total_size() -> int:
        return sum(path.stat().st_size for path in paths if path.exists())

    while paths and total_size() > max_bytes:
        path = paths.pop(0)

        try:
            path.unlink()
        except FileNotFoundError:
            continue


def run_startup_cleanup() -> None:
    cleanup_old_segments()
    compress_old_csvs()
    prune_old_csvs()
    enforce_csv_size_limit()
