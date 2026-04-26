import csv
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import LOG_DIR, MODEL_NAME
from .lexicon import is_us_ham_callsign
from .models import SegmentJob
from .weather_alerts import WeatherAlert


CSV_FIELDS = [
    "event_id",
    "timestamp",
    "feed_name",
    "severity",
    "weather_label",
    "weather_matched",
    "raw_text",
    "normalized_text",
    "radio_codes",
    "radio_numbers",
    "ham_callsigns",
    "duration_seconds",
    "avg_rms",
    "threshold",
    "model",
    "segment_age_seconds",
]


@dataclass(frozen=True)
class EventMetadata:
    event_id: str
    timestamp: str
    radio_codes: str
    radio_numbers: str
    ham_callsigns: str


def daily_csv_path(dt: datetime) -> Path:
    return LOG_DIR / f"scanner-events-{dt:%Y-%m-%d}.csv"


def extract_radio_codes(text: str) -> str:
    matches = re.findall(r"\b((?:10-\d{1,3}|Code \d{1,3}|Signal \d{1,3}|Priority \d)) \[([^\]]+)\]", text)
    return "|".join(f"{code}={meaning}" for code, meaning in matches)


def extract_radio_numbers(text: str) -> str:
    bracket_values = re.findall(r"\[([0-9: ]+(?: to [0-9: ]+)?)\]", text)
    return "|".join(value.strip() for value in bracket_values if value.strip())


def extract_ham_callsigns(text: str) -> str:
    callsigns = []

    for match in re.findall(r"\b[A-Z]{1,3}\d[A-Z]{1,4}\b", text):
        if is_us_ham_callsign(match):
            callsigns.append(match)

    return "|".join(dict.fromkeys(callsigns))


def event_metadata(dt: datetime, normalized_text: str) -> EventMetadata:
    event_id = f"{dt:%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"

    return EventMetadata(
        event_id=event_id,
        timestamp=dt.isoformat(timespec="seconds"),
        radio_codes=extract_radio_codes(normalized_text),
        radio_numbers=extract_radio_numbers(normalized_text),
        ham_callsigns=extract_ham_callsigns(normalized_text),
    )


def append_event_csv(
    job: SegmentJob,
    raw_text: str,
    normalized_text: str,
    alert: WeatherAlert | None,
    metadata: EventMetadata,
    segment_age_seconds: float,
) -> None:
    path = daily_csv_path(datetime.fromisoformat(metadata.timestamp))
    path.parent.mkdir(parents=True, exist_ok=True)
    should_write_header = not path.exists() or path.stat().st_size == 0

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)

        if should_write_header:
            writer.writeheader()

        writer.writerow(
            {
                "event_id": metadata.event_id,
                "timestamp": metadata.timestamp,
                "feed_name": job.feed_name,
                "severity": alert.severity if alert else 0,
                "weather_label": alert.label if alert else "",
                "weather_matched": alert.matched if alert else "",
                "raw_text": raw_text,
                "normalized_text": normalized_text,
                "radio_codes": metadata.radio_codes,
                "radio_numbers": metadata.radio_numbers,
                "ham_callsigns": metadata.ham_callsigns,
                "duration_seconds": f"{job.duration_seconds:.3f}",
                "avg_rms": f"{job.avg_rms:.6f}",
                "threshold": f"{job.threshold:.6f}",
                "model": MODEL_NAME,
                "segment_age_seconds": f"{segment_age_seconds:.3f}",
            }
        )
