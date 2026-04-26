import hashlib
import queue
import re
import time
from collections import deque
from datetime import datetime
from difflib import SequenceMatcher

from .asr import load_model, transcribe_segment
from .config import (
    ASR_SERVER_URL,
    DEDUP_SIMILARITY,
    DEDUP_WINDOW_SECONDS,
    MIN_WORDS,
    MODEL_NAME,
    OUTFILE,
    RADIO_PHONETICS_FILE,
    RADIO_UNITS_FILE,
    RAW_OUTFILE,
    SCANNER_CODES_FILE,
    STALE_JOB_SECONDS,
    WRITE_RAW_LOG,
    WRITE_TEXT_LOG,
    debug,
)
from .csv_log import append_event_csv, event_metadata
from .health import mark_loop, mark_transcript
from .lexicon import (
    load_radio_aliases,
    load_radio_phonetics,
    load_scanner_codes,
    looks_like_radio_code,
    normalize_radio_language,
)
from .models import RadioAlias, ScannerCode, SegmentJob
from .weather_alerts import detect_weather_alert, format_terminal_block


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    text = re.sub(r"\s+([,.!?;:]\s*)", r"\1", text)
    text = re.sub(r"([.!?])\s+", r"\1\n", text)
    return text.strip()


def normalized_hash(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "", text.lower())
    return hashlib.sha1(cleaned.encode("utf-8")).hexdigest()


def similarity(a: str, b: str) -> float:
    a_clean = re.sub(r"[^a-z0-9 ]+", "", a.lower())
    b_clean = re.sub(r"[^a-z0-9 ]+", "", b.lower())
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def looks_like_model_loop(text: str) -> bool:
    words = re.findall(r"[a-z0-9]+", text.lower())

    if len(words) < 10:
        return False

    return len(set(words)) / len(words) < 0.35


class TranscriptWriter:
    def __init__(
        self,
        scanner_codes: dict[str, ScannerCode],
        radio_aliases: list[RadioAlias],
        phonetics: dict[str, str],
    ):
        self.recent_by_feed: dict[str, deque[tuple[float, str, str]]] = {}
        self.scanner_codes = scanner_codes
        self.radio_aliases = radio_aliases
        self.phonetics = phonetics

    def should_drop_duplicate(self, feed_name: str, text: str) -> bool:
        now = time.time()
        digest = normalized_hash(text)
        recent = self.recent_by_feed.setdefault(feed_name, deque())

        while recent and now - recent[0][0] > DEDUP_WINDOW_SECONDS:
            recent.popleft()

        for _seen_at, seen_digest, seen_text in recent:
            if digest == seen_digest:
                return True

            if similarity(text, seen_text) >= DEDUP_SIMILARITY:
                return True

        recent.append((now, digest, text))
        return False

    def append(self, job: SegmentJob, normalized_text: str, raw_text: str, segment_age_seconds: float) -> None:
        dt = datetime.fromtimestamp(job.started_at).astimezone()
        timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
        alert = detect_weather_alert(normalized_text)
        metadata = event_metadata(dt, normalized_text)
        terminal_block = format_terminal_block(timestamp, job.feed_name, normalized_text, alert=alert)
        file_block = f"[{timestamp}] [{job.feed_name}]\n{normalized_text}\n\n"

        print(terminal_block, end="", flush=True)
        append_event_csv(job, raw_text, normalized_text, alert, metadata, segment_age_seconds)
        mark_transcript()

        if WRITE_TEXT_LOG:
            with OUTFILE.open("a", encoding="utf-8") as f:
                f.write(file_block)

        if WRITE_RAW_LOG:
            with RAW_OUTFILE.open("a", encoding="utf-8") as f:
                f.write(
                    f"[{timestamp}] [{job.feed_name}]\n"
                    f"normalized: {normalized_text}\n"
                    f"raw: {raw_text}\n\n"
                )


def transcribe_loop(jobs: queue.Queue[SegmentJob], stop_event) -> None:
    if ASR_SERVER_URL:
        print(f"Using ASR server: {ASR_SERVER_URL}", flush=True)
    else:
        print(f"Loading model: {MODEL_NAME}", flush=True)

    model = load_model()

    scanner_codes = load_scanner_codes()
    radio_aliases = load_radio_aliases()
    phonetics = load_radio_phonetics()

    print(f"Loaded scanner codes: {len(scanner_codes)} from {SCANNER_CODES_FILE}", flush=True)
    print(f"Loaded radio aliases: {len(radio_aliases)} from {RADIO_UNITS_FILE}", flush=True)
    print(f"Loaded radio phonetics: {len(phonetics)} from {RADIO_PHONETICS_FILE}", flush=True)

    writer = TranscriptWriter(scanner_codes, radio_aliases, phonetics)

    print(f"Writing transcript to: {OUTFILE.resolve()}", flush=True)

    while not stop_event.is_set():
        mark_loop()

        try:
            job = jobs.get(timeout=0.5)
        except queue.Empty:
            continue

        try:
            age = time.time() - job.started_at

            if age > STALE_JOB_SECONDS:
                debug(f"[{job.feed_name}] dropped stale segment age={age:.1f}s path={job.path.name}")
                continue

            text = normalize_text(transcribe_segment(job.path, model, job.feed_name))
            normalized_text = normalize_radio_language(
                text,
                scanner_codes,
                radio_aliases,
                phonetics,
                feed_name=job.feed_name,
            )

            if len(normalized_text.split()) < MIN_WORDS and not looks_like_radio_code(normalized_text, scanner_codes):
                debug(f"[{job.feed_name}] dropped short transcript: {text!r}")
                continue

            if looks_like_model_loop(text):
                debug(f"[{job.feed_name}] dropped model loop: {text!r}")
                continue

            if writer.should_drop_duplicate(job.feed_name, normalized_text):
                debug(f"[{job.feed_name}] dropped duplicate: {normalized_text!r}")
                continue

            writer.append(job, normalized_text, text, age)

        except Exception as exc:
            print(f"[{job.feed_name}] failed to transcribe {job.path.name}: {exc}", flush=True)

        finally:
            job.path.unlink(missing_ok=True)
            jobs.task_done()
