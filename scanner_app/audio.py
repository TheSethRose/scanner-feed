import queue
import subprocess
import threading
import time
import uuid
from collections import deque
from pathlib import Path

import numpy as np
import soundfile as sf

from .config import (
    AUDIO_STATS,
    DEBUG,
    END_SILENCE_SECONDS,
    FFMPEG_AUDIO_FILTER,
    FRAME_SECONDS,
    MAX_SEGMENT_SECONDS,
    MIN_RMS,
    MIN_SEGMENT_SECONDS,
    NOISE_PERCENTILE,
    PRE_ROLL_SECONDS,
    SAMPLE_RATE,
    SPEECH_RATIO,
    START_SPEECH_SECONDS,
    STARTUP_SKIP_SECONDS,
    STATS_INTERVAL_SECONDS,
    WORKDIR,
    debug,
)
from .models import Feed, SegmentJob


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
        "-af",
        FFMPEG_AUDIO_FILTER,
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

            if len(rms_history) >= 6:
                noise_floor = float(np.percentile(list(rms_history), NOISE_PERCENTILE))
            else:
                noise_floor = MIN_RMS

            threshold = max(MIN_RMS, noise_floor * SPEECH_RATIO)
            is_speech = frame_rms >= threshold

            if not in_speech and not is_speech:
                rms_history.append(frame_rms)

            stats_window_rms.append(frame_rms)
            now = time.time()

            if (AUDIO_STATS or DEBUG) and now - last_stats_at >= STATS_INTERVAL_SECONDS:
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
                speech_frames = speech_frames + 1 if is_speech else 0

                if speech_frames >= start_frames_needed:
                    in_speech = True
                    silence_frames = 0
                    current_started_at = time.time()
                    current_threshold = threshold
                    current_frames = list(pre_roll)
                    current_rms_values = [frame_rms]
                    debug(f"[{self.feed.name}] speech START rms={frame_rms:.4f} threshold={threshold:.4f}")

                continue

            current_frames.append(audio)
            current_rms_values.append(frame_rms)
            silence_frames = 0 if is_speech else silence_frames + 1

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
