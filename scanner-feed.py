#!/usr/bin/env python3

import csv
import hashlib
import os
import queue
import re
import signal
import subprocess
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import soundfile as sf
from parakeet_mlx import from_pretrained


# ----------------------------
# Config
# ----------------------------

MODEL_NAME = os.getenv("PARAKEET_MODEL", "mlx-community/parakeet-tdt-0.6b-v3")

WORKDIR = Path(os.getenv("WORKDIR", "/tmp/scanner-parakeet"))
OUTFILE = Path(os.getenv("OUTFILE", "./scanner-feed.txt"))
SCANNER_CODES_FILE = Path(os.getenv("SCANNER_CODES_FILE", "./scanner-codes.csv"))

SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))
FRAME_SECONDS = float(os.getenv("FRAME_SECONDS", "0.50"))

# Generic Broadcastify/startup guard.
# This is not text filtering. It just ignores the first N seconds after connecting.
STARTUP_SKIP_SECONDS = float(os.getenv("STARTUP_SKIP_SECONDS", "0"))

# Adaptive speech detection.
MIN_RMS = float(os.getenv("MIN_RMS", "0.0015"))
SPEECH_RATIO = float(os.getenv("SPEECH_RATIO", "3.0"))
NOISE_PERCENTILE = float(os.getenv("NOISE_PERCENTILE", "20"))

START_SPEECH_SECONDS = float(os.getenv("START_SPEECH_SECONDS", "0.75"))
END_SILENCE_SECONDS = float(os.getenv("END_SILENCE_SECONDS", "1.25"))
PRE_ROLL_SECONDS = float(os.getenv("PRE_ROLL_SECONDS", "1.0"))

MIN_SEGMENT_SECONDS = float(os.getenv("MIN_SEGMENT_SECONDS", "0.5"))
MAX_SEGMENT_SECONDS = float(os.getenv("MAX_SEGMENT_SECONDS", "22"))

MIN_WORDS = int(os.getenv("MIN_WORDS", "1"))
DEDUP_WINDOW_SECONDS = float(os.getenv("DEDUP_WINDOW_SECONDS", "60"))
DEDUP_SIMILARITY = float(os.getenv("DEDUP_SIMILARITY", "0.92"))

DEBUG = os.getenv("DEBUG", "0") == "1"
AUDIO_STATS = os.getenv("AUDIO_STATS", "0") == "1"
STATS_INTERVAL_SECONDS = float(os.getenv("STATS_INTERVAL_SECONDS", "5"))

WORKDIR.mkdir(parents=True, exist_ok=True)
OUTFILE.parent.mkdir(parents=True, exist_ok=True)


# ----------------------------
# Feed parsing
# ----------------------------

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


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip())
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "feed"


def load_feeds() -> list[Feed]:
    """
    Supported formats:

    Single feed:
      FEED_URL=https://broadcastify.cdnstream1.com/31880

    Multiple feeds:
      FEEDS="Plano|https://broadcastify.cdnstream1.com/31880,Allen|https://example.com/feed"

    File:
      FEEDS_FILE=feeds.txt

    feeds.txt format:
      Plano|https://broadcastify.cdnstream1.com/31880
      Allen|https://example.com/feed
    """

    feeds_file = os.getenv("FEEDS_FILE")
    feeds_raw = os.getenv("FEEDS")

    lines: list[str] = []

    if feeds_file:
        path = Path(feeds_file)
        lines.extend(path.read_text(encoding="utf-8").splitlines())

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


# ----------------------------
# Audio segmentation
# ----------------------------

def start_ffmpeg(url: str) -> subprocess.Popen:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-reconnect",
        "1",
        "-reconnect_streamed",
        "1",
        "-reconnect_delay_max",
        "5",
        "-i",
        url,
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-f",
        "s16le",
        "pipe:1",
    ]

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )


def pcm16_to_float32(raw: bytes) -> np.ndarray:
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    return audio / 32768.0


def rms(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0

    return float(np.sqrt(np.mean(np.square(audio))))


def write_segment(feed_name: str, audio: np.ndarray) -> Path:
    filename = f"{feed_name}-{int(time.time())}-{uuid.uuid4().hex[:8]}.wav"
    path = WORKDIR / filename
    sf.write(path, audio, SAMPLE_RATE)
    return path


def debug(message: str) -> None:
    if DEBUG:
        print(message, flush=True)


# ----------------------------
# Scanner code lookup
# ----------------------------

NUMBER_WORDS = {
    "zero": 0,
    "oh": 0,
    "o": 0,
    "one": 1,
    "two": 2,
    "to": 2,
    "too": 2,
    "three": 3,
    "four": 4,
    "for": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "ate": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fourty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}

STRUCTURED_CODE_PREFIXES = ("code", "signal", "priority")
CODE_WORDS = {word for word in NUMBER_WORDS if word not in {"to", "too", "for"}}


def load_scanner_codes() -> dict[str, ScannerCode]:
    if not SCANNER_CODES_FILE.exists():
        debug(f"scanner code file not found: {SCANNER_CODES_FILE}")
        return {}

    scanner_codes: dict[str, ScannerCode] = {}

    with SCANNER_CODES_FILE.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = (row.get("code") or "").strip()

            if not code:
                continue

            scanner_codes[normalize_code_key(code)] = ScannerCode(
                code_type=(row.get("code_type") or "").strip(),
                code=code,
                meaning=(row.get("meaning") or "").strip(),
                category=(row.get("category") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            )

    return scanner_codes


def normalize_code_key(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"\bten[\s-]+(\d{1,3})\b", r"10-\1", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s*-\s*", "-", value)

    return value


def parse_number_words(words: list[str]) -> int | None:
    if not words:
        return None

    total = 0
    current = 0
    consumed = False

    for word in words:
        value = NUMBER_WORDS.get(word)

        if value is None:
            return None

        consumed = True

        if value == 100:
            current = max(current, 1) * 100
        elif value >= 20:
            current += value
        else:
            current += value

    if not consumed:
        return None

    total += current
    return total


def spoken_number_candidates(words: list[str]) -> list[int]:
    number = parse_number_words(words)

    if number is None:
        return []

    candidates = [number]

    if len(words) > 1:
        pieces = []

        for word in words:
            value = NUMBER_WORDS.get(word)

            if value is None:
                return candidates

            pieces.append(str(value))

        digits = "".join(pieces)

        if digits and digits.isdigit():
            candidates.append(int(digits))

    return list(dict.fromkeys(candidates))


def short_meaning(meaning: str) -> str:
    meaning = meaning.split("/", 1)[0]
    meaning = meaning.split(" - ", 1)[0]
    meaning = meaning.split("(", 1)[0]
    return meaning.strip()


def token_spans(text: str) -> list[tuple[str, int, int]]:
    return [
        (match.group(0).lower(), match.start(), match.end())
        for match in re.finditer(r"[a-z0-9]+", text, flags=re.IGNORECASE)
    ]


def numbers_from_token(token: str) -> list[int]:
    if token.isdigit():
        return [int(token)]

    if token in CODE_WORDS:
        return spoken_number_candidates([token])

    return []


def find_code_annotations(text: str, scanner_codes: dict[str, ScannerCode]) -> list[tuple[int, int, str]]:
    tokens = token_spans(text)
    annotations: list[tuple[int, int, str]] = []

    for index, (token, start, _end) in enumerate(tokens):
        if token == "10" and index + 1 < len(tokens):
            for number in numbers_from_token(tokens[index + 1][0]):
                key = normalize_code_key(f"10-{number}")

                if key in scanner_codes:
                    entry = scanner_codes[key]
                    annotations.append((start, tokens[index + 1][2], short_meaning(entry.meaning)))
                    break

        if token == "ten":
            best: tuple[int, ScannerCode] | None = None

            for end_index in range(index + 2, min(len(tokens), index + 5) + 1):
                words = [part[0] for part in tokens[index + 1:end_index]]

                if not words or any(word not in CODE_WORDS for word in words):
                    break

                for number in spoken_number_candidates(words):
                    key = normalize_code_key(f"10-{number}")

                    if key in scanner_codes:
                        best = (end_index - 1, scanner_codes[key])

            if best:
                end_index, entry = best
                annotations.append((start, tokens[end_index][2], short_meaning(entry.meaning)))

        if token in STRUCTURED_CODE_PREFIXES:
            best = None

            for end_index in range(index + 2, min(len(tokens), index + 4) + 1):
                words = [part[0] for part in tokens[index + 1:end_index]]

                if not words or any(word not in CODE_WORDS and not word.isdigit() for word in words):
                    break

                candidates = [int(words[0])] if len(words) == 1 and words[0].isdigit() else spoken_number_candidates(words)

                for number in candidates:
                    key = normalize_code_key(f"{token} {number}")

                    if key in scanner_codes:
                        best = (end_index - 1, scanner_codes[key])

            if best:
                end_index, entry = best
                annotations.append((start, tokens[end_index][2], short_meaning(entry.meaning)))

    return annotations


def radio_number_from_words(words: list[str]) -> str:
    parts: list[str] = []
    index = 0

    while index < len(words):
        word = words[index]
        value = NUMBER_WORDS.get(word)

        if value is None:
            index += 1
            continue

        next_value = NUMBER_WORDS.get(words[index + 1]) if index + 1 < len(words) else None

        if value >= 20 and next_value is not None and 0 <= next_value <= 9:
            parts.append(str(value + next_value))
            index += 2
            continue

        if value == 100 and parts:
            parts[-1] = str(int(parts[-1]) * 100)
        else:
            parts.append(str(value))

        index += 1

    return "".join(parts)


def find_radio_number_annotations(text: str) -> list[tuple[int, int, str]]:
    annotations: list[tuple[int, int, str]] = []

    for segment_match in re.finditer(r"[^.!?\n]+", text):
        segment = segment_match.group(0)
        offset = segment_match.start()
        tokens = token_spans(segment)
        index = 0

        while index < len(tokens):
            token = tokens[index][0]

            if token not in NUMBER_WORDS or token == "to":
                index += 1
                continue

            start = index
            groups: list[list[str]] = [[]]
            has_separator = False

            while index < len(tokens):
                current = tokens[index][0]
                next_token = tokens[index + 1][0] if index + 1 < len(tokens) else ""

                if current == "to" and groups[-1] and next_token in NUMBER_WORDS and next_token != "to":
                    has_separator = True
                    groups.append([])
                    index += 1
                    continue

                if current not in NUMBER_WORDS or current == "to":
                    break

                groups[-1].append(current)
                index += 1

            words = [part[0] for part in tokens[start:index]]
            converted_groups = [radio_number_from_words(group) for group in groups if group]
            converted = " to ".join(converted_groups)

            if converted and (has_separator or len(converted.replace(" to ", "")) >= 4):
                annotations.append((offset + tokens[start][1], offset + tokens[index - 1][2], converted))

            if index == start:
                index += 1

    return annotations


def annotate_transcript_text(text: str, scanner_codes: dict[str, ScannerCode]) -> str:
    annotations = find_code_annotations(text, scanner_codes)
    occupied: list[tuple[int, int]] = [(start, end) for start, end, _label in annotations]

    for start, end, label in find_radio_number_annotations(text):
        if any(start < occupied_end and end > occupied_start for occupied_start, occupied_end in occupied):
            continue

        annotations.append((start, end, label))
        occupied.append((start, end))

    if not annotations:
        return text

    result = text

    for start, end, label in sorted(annotations, key=lambda item: item[0], reverse=True):
        result = f"{result[:end]} [{label}]{result[end:]}"

    return result


class FeedWorker(threading.Thread):
    def __init__(self, feed: Feed, jobs: queue.Queue[SegmentJob], stop_event: threading.Event):
        super().__init__(daemon=True)
        self.feed = feed
        self.jobs = jobs
        self.stop_event = stop_event

    def run(self) -> None:
        while not self.stop_event.is_set():
            ffmpeg = None

            try:
                debug(f"[{self.feed.name}] connecting")
                ffmpeg = start_ffmpeg(self.feed.url)

                if ffmpeg.stdout is None:
                    raise RuntimeError("ffmpeg stdout was not available")

                self.read_stream(ffmpeg)

            except Exception as exc:
                debug(f"[{self.feed.name}] worker error: {exc}")

            finally:
                if ffmpeg:
                    ffmpeg.kill()

            if not self.stop_event.is_set():
                debug(f"[{self.feed.name}] reconnecting in 3 seconds")
                time.sleep(3)

    def read_stream(self, ffmpeg: subprocess.Popen) -> None:
        frame_bytes = int(SAMPLE_RATE * FRAME_SECONDS * 2)
        start_frames_needed = max(1, int(START_SPEECH_SECONDS / FRAME_SECONDS))
        end_frames_needed = max(1, int(END_SILENCE_SECONDS / FRAME_SECONDS))
        pre_roll_frames_needed = max(1, int(PRE_ROLL_SECONDS / FRAME_SECONDS))
        max_segment_frames = max(1, int(MAX_SEGMENT_SECONDS / FRAME_SECONDS))
        min_segment_frames = max(1, int(MIN_SEGMENT_SECONDS / FRAME_SECONDS))

        has_announced_connected = False

        rms_history: deque[float] = deque(maxlen=int(90 / FRAME_SECONDS))
        pre_roll: deque[np.ndarray] = deque(maxlen=pre_roll_frames_needed)

        in_speech = False
        speech_frames = 0
        silence_frames = 0

        current_frames: list[np.ndarray] = []
        current_rms_values: list[float] = []
        current_started_at = 0.0
        current_threshold = 0.0

        last_stats_at = 0.0
        stats_window_rms: list[float] = []
        raw_buffer = bytearray()
        skipped_audio_seconds = 0.0

        while not self.stop_event.is_set():
            chunk = ffmpeg.stdout.read(frame_bytes)

            if not chunk:
                raise RuntimeError("ffmpeg stream ended")

            raw_buffer.extend(chunk)

            if len(raw_buffer) < frame_bytes:
                continue

            raw = bytes(raw_buffer[:frame_bytes])
            del raw_buffer[:frame_bytes]

            if not has_announced_connected:
                has_announced_connected = True
                debug(f"[{self.feed.name}] connected")

            audio = pcm16_to_float32(raw)
            frame_rms = rms(audio)

            # Calculate threshold from existing history (history only contains silence frames)
            if len(rms_history) >= 6:
                noise_floor = float(np.percentile(list(rms_history), NOISE_PERCENTILE))
            else:
                noise_floor = MIN_RMS

            threshold = max(MIN_RMS, noise_floor * SPEECH_RATIO)
            is_speech = frame_rms >= threshold

            # Only add to noise history when we are NOT in speech AND this frame is silence.
            # This prevents speech from polluting the noise floor estimate.
            if not in_speech and not is_speech:
                rms_history.append(frame_rms)

            stats_window_rms.append(frame_rms)
            now = time.time()
            if (DEBUG or AUDIO_STATS) and now - last_stats_at >= STATS_INTERVAL_SECONDS:
                last_stats_at = now
                avg_rms = float(np.mean(stats_window_rms)) if stats_window_rms else 0.0
                max_rms = float(np.max(stats_window_rms)) if stats_window_rms else 0.0
                min_rms = float(np.min(stats_window_rms)) if stats_window_rms else 0.0
                status = "SPEECH" if in_speech else "silence"
                print(
                    f"[{self.feed.name}] levels min={min_rms:.4f} avg={avg_rms:.4f} max={max_rms:.4f} "
                    f"threshold={threshold:.4f} noise_floor={noise_floor:.4f} {status} "
                    f"history={len(rms_history)}",
                    flush=True,
                )
                stats_window_rms.clear()

            if AUDIO_STATS:
                print(
                    f"[{self.feed.name}] frame rms={frame_rms:.4f} threshold={threshold:.4f} speech={is_speech}",
                    flush=True,
                )

            if skipped_audio_seconds < STARTUP_SKIP_SECONDS:
                skipped_audio_seconds += FRAME_SECONDS
                pre_roll.append(audio)
                continue

            if not in_speech:
                pre_roll.append(audio)

                if is_speech:
                    speech_frames += 1
                else:
                    speech_frames = 0

                if speech_frames >= start_frames_needed:
                    in_speech = True
                    silence_frames = 0
                    current_started_at = time.time()
                    current_threshold = threshold
                    current_frames = list(pre_roll)
                    current_rms_values = [frame_rms]
                    debug(
                        f"[{self.feed.name}] speech START rms={frame_rms:.4f} threshold={threshold:.4f}"
                    )

                continue

            current_frames.append(audio)
            current_rms_values.append(frame_rms)

            if is_speech:
                silence_frames = 0
            else:
                silence_frames += 1

            hit_end_silence = silence_frames >= end_frames_needed
            hit_max_duration = len(current_frames) >= max_segment_frames

            if hit_end_silence or hit_max_duration:
                usable_frames = current_frames[:-silence_frames] if hit_end_silence else current_frames

                if len(usable_frames) >= min_segment_frames:
                    segment_audio = np.concatenate(usable_frames)
                    duration = len(segment_audio) / SAMPLE_RATE
                    path = write_segment(self.feed.name, segment_audio)

                    self.jobs.put(
                        SegmentJob(
                            feed_name=self.feed.name,
                            path=path,
                            started_at=current_started_at,
                            duration_seconds=duration,
                            avg_rms=float(np.mean(current_rms_values)),
                            threshold=current_threshold,
                        )
                    )

                    debug(
                        f"[{self.feed.name}] queued {path.name} "
                        f"duration={duration:.1f}s avg_rms={np.mean(current_rms_values):.4f} "
                        f"threshold={current_threshold:.4f}"
                    )
                else:
                    debug(
                        f"[{self.feed.name}] dropped short segment "
                        f"frames={len(usable_frames)}/{min_segment_frames} "
                        f"duration~={len(usable_frames) * FRAME_SECONDS:.1f}s"
                    )

                in_speech = False
                speech_frames = 0
                silence_frames = 0
                current_frames = []
                current_rms_values = []
                pre_roll.clear()
                debug(f"[{self.feed.name}] speech END")


# ----------------------------
# Transcription
# ----------------------------

def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    text = re.sub(r"\s+([,.!?;:]\s*)", r"\1", text)
    text = re.sub(r"([.!?])\s+", r"\1\n", text)

    return text.strip()


def extract_text(result) -> str:
    if hasattr(result, "sentences") and result.sentences:
        lines = []

        for sentence in result.sentences:
            sentence_text = getattr(sentence, "text", "").strip()

            if sentence_text:
                lines.append(sentence_text)

        if lines:
            return "\n".join(lines)

    if hasattr(result, "text"):
        return result.text

    return str(result)


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

    unique_ratio = len(set(words)) / len(words)

    return unique_ratio < 0.35


class TranscriptWriter:
    def __init__(self, scanner_codes: dict[str, ScannerCode]):
        self.recent_by_feed: dict[str, deque[tuple[float, str, str]]] = {}
        self.scanner_codes = scanner_codes

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

    def append(self, job: SegmentJob, text: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(job.started_at))
        body = annotate_transcript_text(text, self.scanner_codes)

        block = (
            f"[{timestamp}] [{job.feed_name}]\n"
            f"{body}\n\n"
        )

        print(block, end="", flush=True)

        with OUTFILE.open("a", encoding="utf-8") as f:
            f.write(block)


def transcribe_loop(jobs: queue.Queue[SegmentJob], stop_event: threading.Event) -> None:
    print(f"Loading model: {MODEL_NAME}", flush=True)
    model = from_pretrained(MODEL_NAME)

    scanner_codes = load_scanner_codes()
    print(f"Loaded scanner codes: {len(scanner_codes)} from {SCANNER_CODES_FILE}", flush=True)
    writer = TranscriptWriter(scanner_codes)

    print(f"Writing transcript to: {OUTFILE.resolve()}", flush=True)

    while not stop_event.is_set():
        try:
            job = jobs.get(timeout=0.5)
        except queue.Empty:
            continue

        try:
            result = model.transcribe(str(job.path))
            text = normalize_text(extract_text(result))

            if len(text.split()) < MIN_WORDS:
                debug(f"[{job.feed_name}] dropped short transcript: {text!r}")
                continue

            if looks_like_model_loop(text):
                debug(f"[{job.feed_name}] dropped model loop: {text!r}")
                continue

            if writer.should_drop_duplicate(job.feed_name, text):
                debug(f"[{job.feed_name}] dropped duplicate: {text!r}")
                continue

            writer.append(job, text)

        except Exception as exc:
            print(f"[{job.feed_name}] failed to transcribe {job.path.name}: {exc}", flush=True)

        finally:
            job.path.unlink(missing_ok=True)
            jobs.task_done()


# ----------------------------
# Main
# ----------------------------

def main() -> None:
    feeds = load_feeds()
    stop_event = threading.Event()
    jobs: queue.Queue[SegmentJob] = queue.Queue(maxsize=200)

    print("Configured feeds:", flush=True)

    for feed in feeds:
        print(f"  - {feed.name}: {feed.url}", flush=True)

    workers = [
        FeedWorker(feed=feed, jobs=jobs, stop_event=stop_event)
        for feed in feeds
    ]

    for worker in workers:
        worker.start()

    def shutdown(_signum, _frame):
        print("\nStopping...", flush=True)
        stop_event.set()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    transcribe_loop(jobs, stop_event)


if __name__ == "__main__":
    main()
