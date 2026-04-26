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
python scanner.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FEED_URL` | `https://broadcastify.cdnstream1.com/31880` | Audio stream URL |
| `FEEDS_FILE` | unset | File containing one `Name|URL` feed per line |
| `PARAKEET_MODEL` | `mlx-community/parakeet-tdt-0.6b-v3` | MLX model to load |
| `WORKDIR` | `/tmp/scanner-parakeet` | Temp chunk directory |
| `OUTFILE` | `./scanner-feed.txt` | Transcript output path |
| `RAW_OUTFILE` | `./scanner-feed.raw.txt` | Audit log containing normalized and raw transcripts |
| `SCANNER_CODES_FILE` | `./data/scanner-codes.csv` | Trimmed CSV reference used for inline radio-code annotations |
| `RADIO_UNITS_FILE` | `./data/radio-units.csv` | Radio unit, agency, and phrase alias normalization |
| `RADIO_PHONETICS_FILE` | `./data/radio-phonetics.csv` | Public-safety phonetic spelling normalization |
| `FFMPEG_AUDIO_FILTER` | voice-band cleanup chain | ffmpeg filter applied before segmentation and transcription |
| `STARTUP_SKIP_SECONDS` | `0` | Audio seconds to ignore after connecting |
| `MIN_RMS` | `0.0015` | Minimum audio level to process |
| `START_SPEECH_SECONDS` | `0.5` | Speech needed before opening a segment |
| `END_SILENCE_SECONDS` | `0.9` | Silence needed before closing a segment |
| `PRE_ROLL_SECONDS` | `0.75` | Audio kept before detected speech |
| `MIN_SEGMENT_SECONDS` | `1.0` | Minimum detected speech segment length |
| `MAX_SEGMENT_SECONDS` | `18` | Maximum segment length before forced transcription |
| `MIN_WORDS` | `3` | Minimum words to keep a transcript |
| `DEDUP_SIMILARITY` | `0.88` | Similarity cutoff for duplicate suppression |
| `STALE_JOB_SECONDS` | `75` | Drop queued segments older than this |

## Tuning

Lower `MIN_RMS` if it skips quiet dispatch audio. Higher if it transcribes static.

```bash
FEEDS_FILE=feeds.txt python scanner.py
```

For a noisier but more complete feed, lower `MIN_WORDS` back to `1`.

The main log writes normalized text. The raw audit log keeps both forms:

```text
normalized: 10-4 [Acknowledged]
raw: Ten four.
```
