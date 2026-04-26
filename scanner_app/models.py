from dataclasses import dataclass
from pathlib import Path


@dataclass
class Feed:
    name: str
    url: str


@dataclass
class SegmentJob:
    feed_name: str
    path: Path
    started_at: float
    duration_seconds: float
    avg_rms: float
    threshold: float


@dataclass(frozen=True)
class ScannerCode:
    code_type: str
    code: str
    meaning: str
    category: str
    notes: str


@dataclass(frozen=True)
class RadioAlias:
    term_type: str
    canonical: str
    aliases: tuple[str, ...]
    notes: str
