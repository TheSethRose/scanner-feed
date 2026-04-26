import os
import re
from pathlib import Path

from .models import Feed


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip())
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "feed"


def load_feeds() -> list[Feed]:
    feeds_file = os.getenv("FEEDS_FILE")
    feeds_raw = os.getenv("FEEDS")
    lines: list[str] = []

    if feeds_file:
        lines.extend(Path(feeds_file).read_text(encoding="utf-8").splitlines())

    if feeds_raw:
        lines.extend(feeds_raw.split(","))

    if not lines:
        feed_url = os.getenv("FEED_URL", "https://broadcastify.cdnstream1.com/31880")
        lines.append(f"scanner|{feed_url}")

    feeds: list[Feed] = []

    for index, line in enumerate(lines, start=1):
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "|" in line:
            name, url = line.split("|", 1)
        else:
            name, url = f"feed-{index}", line

        feeds.append(Feed(name=slugify(name), url=url.strip()))

    if not feeds:
        raise RuntimeError("No feeds configured.")

    return feeds
