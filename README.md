# Scanner Feed Transcription

Live transcription of scanner audio feeds using NVIDIA Parakeet via MLX.

## Install

```bash
brew install ffmpeg
python3 -m venv .venv
source .venv/bin/activate
pip install -U parakeet-mlx numpy soundfile
```

## Run

```bash
python scanner-feed.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FEED_URL` | `https://broadcastify.cdnstream1.com/31880` | Audio stream URL |
| `FEEDS_FILE` | unset | File containing one `Name|URL` feed per line |
| `PARAKEET_MODEL` | `mlx-community/parakeet-tdt-0.6b-v3` | MLX model to load |
| `WORKDIR` | `/tmp/scanner-parakeet` | Temp chunk directory |
| `OUTFILE` | `./scanner-feed.txt` | Transcript output path |
| `SCANNER_CODES_FILE` | `./scanner-codes.csv` | Trimmed CSV reference used for inline radio-code annotations |
| `STARTUP_SKIP_SECONDS` | `0` | Audio seconds to ignore after connecting |
| `MIN_RMS` | `0.0015` | Minimum audio level to process |
| `MIN_SEGMENT_SECONDS` | `0.5` | Minimum detected speech segment length |
| `MIN_WORDS` | `1` | Minimum words to keep a transcript |

## Tuning

Lower `MIN_RMS` if it skips quiet dispatch audio. Higher if it transcribes static.

```bash
FEEDS_FILE=feeds.txt python scanner-feed.py
```
