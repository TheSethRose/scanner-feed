import os
from pathlib import Path


MODEL_NAME = os.getenv("PARAKEET_MODEL", "mlx-community/parakeet-tdt-0.6b-v3")
ASR_SERVER_URL = os.getenv("ASR_SERVER_URL", "").rstrip("/")
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "49173"))

WORKDIR = Path(os.getenv("WORKDIR", "/tmp/scanner-parakeet"))
OUTFILE = Path(os.getenv("OUTFILE", "./scanner-feed.txt"))
RAW_OUTFILE = Path(os.getenv("RAW_OUTFILE", "./scanner-feed.raw.txt"))
LOG_DIR = Path(os.getenv("LOG_DIR", "./logs"))
SCANNER_CODES_FILE = Path(os.getenv("SCANNER_CODES_FILE", "./data/scanner-codes.csv"))
RADIO_UNITS_FILE = Path(os.getenv("RADIO_UNITS_FILE", "./data/radio-units.csv"))
RADIO_PHONETICS_FILE = Path(os.getenv("RADIO_PHONETICS_FILE", "./data/radio-phonetics.csv"))

SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))
FRAME_SECONDS = float(os.getenv("FRAME_SECONDS", "0.50"))
FFMPEG_AUDIO_FILTER = os.getenv(
    "FFMPEG_AUDIO_FILTER",
    "highpass=f=250,lowpass=f=3400,afftdn=nf=-25,"
    "dynaudnorm=f=75:g=15,"
    "acompressor=threshold=-22dB:ratio=3:attack=5:release=80",
)

STARTUP_SKIP_SECONDS = float(os.getenv("STARTUP_SKIP_SECONDS", "0"))

MIN_RMS = float(os.getenv("MIN_RMS", "0.0015"))
SPEECH_RATIO = float(os.getenv("SPEECH_RATIO", "3.0"))
NOISE_PERCENTILE = float(os.getenv("NOISE_PERCENTILE", "20"))

START_SPEECH_SECONDS = float(os.getenv("START_SPEECH_SECONDS", "0.5"))
END_SILENCE_SECONDS = float(os.getenv("END_SILENCE_SECONDS", "0.9"))
PRE_ROLL_SECONDS = float(os.getenv("PRE_ROLL_SECONDS", "0.75"))

MIN_SEGMENT_SECONDS = float(os.getenv("MIN_SEGMENT_SECONDS", "1.0"))
MAX_SEGMENT_SECONDS = float(os.getenv("MAX_SEGMENT_SECONDS", "18"))

MIN_WORDS = int(os.getenv("MIN_WORDS", "3"))
DEDUP_WINDOW_SECONDS = float(os.getenv("DEDUP_WINDOW_SECONDS", "60"))
DEDUP_SIMILARITY = float(os.getenv("DEDUP_SIMILARITY", "0.88"))
STALE_JOB_SECONDS = float(os.getenv("STALE_JOB_SECONDS", "75"))
WRITE_TEXT_LOG = os.getenv("WRITE_TEXT_LOG", "1") == "1"
WRITE_RAW_LOG = os.getenv("WRITE_RAW_LOG", "1") == "1"
CSV_RETENTION_DAYS = int(os.getenv("CSV_RETENTION_DAYS", "14"))
CSV_MAX_TOTAL_MB = float(os.getenv("CSV_MAX_TOTAL_MB", "500"))
COMPRESS_OLD_CSV_DAYS = int(os.getenv("COMPRESS_OLD_CSV_DAYS", "2"))
SEGMENT_RETENTION_MINUTES = float(os.getenv("SEGMENT_RETENTION_MINUTES", "10"))
KEEP_SEGMENTS = os.getenv("KEEP_SEGMENTS", "0") == "1"

DEBUG = os.getenv("DEBUG", "0") == "1"
AUDIO_STATS = os.getenv("AUDIO_STATS", "0") == "1"
STATS_INTERVAL_SECONDS = float(os.getenv("STATS_INTERVAL_SECONDS", "5"))


def ensure_output_dirs() -> None:
    WORKDIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    RAW_OUTFILE.parent.mkdir(parents=True, exist_ok=True)


def debug(message: str) -> None:
    if DEBUG:
        print(message, flush=True)
