# API Reference

This guide provides API documentation for developers and AI agents working with the scanner feed transcription system.

## Parakeet Server API

The native MLX Parakeet server provides HTTP endpoints for audio transcription.

**Base URL:** `http://127.0.0.1:18765`

### Health Check

**Endpoint:** `GET /health`

**Description:** Check if the Parakeet server is running and ready to transcribe.

**Response:**
```json
{
  "status": "ok",
  "model": "mlx-community/parakeet-tdt-0.6b-v3"
}
```

**Example:**
```bash
curl http://127.0.0.1:18765/health
```

### Transcribe Audio

**Endpoint:** `POST /transcribe`

**Description:** Transcribe an audio file.

**Request Body:**
- Content-Type: `multipart/form-data`
- Form data: `audio` (file field containing WAV/MP3 audio)

**Response:**
```json
{
  "transcription": "ten four",
  "confidence": 0.95,
  "duration": 1.2
}
```

**Example:**
```bash
curl -X POST -F "audio=@/path/to/audio.wav" http://127.0.0.1:18765/transcribe
```

## Docker Worker API

The Docker worker provides health monitoring and status endpoints.

**Base URL:** `http://127.0.0.1:49173`

### Health Check

**Endpoint:** `GET /health`

**Description:** Check if the Docker worker is running and healthy.

**Response:**
```json
{
  "status": "ok",
  "container": "scanner-feed-worker"
}
```

**Example:**
```bash
curl http://127.0.0.1:49173/health
```

## Python API

### Scanner App Modules

The scanner application is organized into several Python modules:

#### `scanner_app.app.py`
Main application entry point.

**Functions:**
- `main()` - Main application loop
- `setup_logging()` - Configure logging
- `load_feeds()` - Load audio feeds from file

#### `scanner_app.asr.py`
Automatic Speech Recognition interface.

**Functions:**
- `transcribe_audio(audio_path)` - Transcribe audio file
- `connect_asr_server(url)` - Connect to ASR server
- `is_asr_available()` - Check ASR server status

#### `scanner_app.audio.py`
Audio processing and feed management.

**Functions:**
- `connect_audio_feed(url)` - Connect to audio stream
- `segment_audio(audio_data)` - Segment audio using VAD
- `apply_audio_filters(audio_data)` - Apply FFmpeg filters

#### `scanner_app.config.py`
Configuration management.

**Functions:**
- `get_config()` - Get configuration dictionary
- `load_config()` - Load configuration from environment
- `validate_config()` - Validate configuration values

#### `scanner_app.feeds.py`
Audio feed management.

**Functions:**
- `load_feeds(file_path)` - Load feeds from file
- `parse_feed_line(line)` - Parse feed line (Name|URL)
- `test_feed(url)` - Test feed connectivity

#### `scanner_app.lexicon.py`
Normalization and lexicon management.

**Functions:**
- `normalize_text(text)` - Normalize transcription text
- `expand_radio_codes(text)` - Expand radio codes
- `normalize_radio_units(text)` - Normalize radio unit names
- `detect_ham_callsigns(text)` - Detect HAM radio callsigns

#### `scanner_app.transcribe.py`
Transcription workflow management.

**Functions:**
- `process_segment(audio_segment)` - Process audio segment
- `queue_transcription(audio_path)` - Queue audio for transcription
- `get_transcription_result()` - Get transcription result

#### `scanner_app.csv_log.py`
CSV logging functionality.

**Functions:**
- `write_csv_event(event_data)` - Write event to CSV log
- `get_csv_log_path()` - Get current CSV log file path
- `cleanup_old_logs()` - Clean up old CSV logs

#### `scanner_app.weather_alerts.py`
Weather alert detection and formatting.

**Functions:**
- `detect_weather_alerts(text)` - Detect weather terms
- `format_weather_alert(alert_level, text)` - Format weather alert
- `get_weather_severity(text)` - Get weather severity level

#### `scanner_app.retention.py`
Log and file retention management.

**Functions:**
- `cleanup_old_csv_logs()` - Clean up old CSV logs
- `compress_old_logs()` - Compress old log files
- `cleanup_temp_segments()` - Clean up temporary audio segments

#### `scanner_app.health.py`
Health monitoring and endpoints.

**Functions:**
- `start_health_server(port)` - Start health endpoint server
- `health_check()` - Perform health check
- `get_system_status()` - Get system status information

## Configuration Reference

### Environment Variables

#### Parakeet Server
| Variable | Default | Description |
|----------|---------|-------------|
| `PARAKEET_SERVER_PORT` | `18765` | Server port |
| `PARAKEET_MODEL` | `mlx-community/parakeet-tdt-0.6b-v3` | MLX model to load |

#### Docker Worker
| Variable | Default | Description |
|----------|---------|-------------|
| `ASR_SERVER_URL` | `http://host.docker.internal:18765` | Parakeet server URL |
| `FEEDS_FILE` | `/app/feeds.txt` | Audio feeds configuration file |
| `WORKDIR` | `/tmp/scanner-parakeet` | Temporary segment directory |
| `LOG_DIR` | `./logs` | CSV log directory |
| `OUTFILE` | `./scanner-feed.txt` | Transcript output file |
| `RAW_OUTFILE` | `./scanner-feed.raw.txt` | Raw audit log file |
| `HEALTH_PORT` | `49173` | Health endpoint port |

#### Audio Processing
| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_RMS` | `0.0015` | Minimum audio level (0.0-1.0) |
| `START_SPEECH_SECONDS` | `0.5` | Speech detection threshold (seconds) |
| `END_SILENCE_SECONDS` | `0.9` | Silence threshold (seconds) |
| `MIN_SEGMENT_SECONDS` | `1.0` | Minimum segment length (seconds) |
| `MAX_SEGMENT_SECONDS` | `18` | Maximum segment length (seconds) |
| `MIN_WORDS` | `3` | Minimum words to keep transcript |
| `DEDUP_SIMILARITY` | `0.88` | Duplicate suppression similarity cutoff |

#### Log Management
| Variable | Default | Description |
|----------|---------|-------------|
| `CSV_RETENTION_DAYS` | `14` | Log retention days |
| `CSV_MAX_TOTAL_MB` | `500` | Max total log size (MB) |
| `COMPRESS_OLD_CSV_DAYS` | `2` | Compression threshold (days) |
| `SEGMENT_RETENTION_MINUTES` | `10` | Temp segment retention (minutes) |
| `KEEP_SEGMENTS` | `0` | Keep temporary segments (0/1) |

## Docker API

### Docker Compose Commands

**Start System:**
```bash
docker compose up -d
```

**Stop System:**
```bash
docker compose down
```

**View Logs:**
```bash
docker compose logs -f scanner
```

**Check Status:**
```bash
docker compose ps
```

**Restart Worker:**
```bash
docker compose restart scanner
```

### Docker Container API

The scanner worker container provides:

**Environment Variables:**
- All configuration via environment variables
- Mounted volumes for logs and runtime data

**Volumes:**
- `/Users/sethrose/Developer/Github/scanner-feed/runtime` - Runtime files
- `/Users/sethrose/Developer/Github/scanner-feed/logs` - Log files

**Ports:**
- `49173` - Health endpoint

## File Formats

### feeds.txt Format

**Format:** `Name|URL`

**Example:**
```
County Dispatch|https://broadcastify.cdnstream1.com/31880
Fire Department|https://broadcastify.cdnstream1.com/12345
```

### CSV Log Format

**Columns:**
1. `timestamp` - Event timestamp (ISO 8601)
2. `feed_name` - Audio feed name
3. `raw_text` - Original transcription
4. `normalized_text` - Normalized transcription
5. `radio_codes` - Detected radio codes
6. `radio_numbers` - Radio unit numbers
7. `ham_callsigns` - HAM radio callsigns
8. `weather_severity` - Weather alert level (WX-1 to WX-4)
9. `rms_level` - Audio level (0.0-1.0)
10. `model` - MLX model used
11. `segment_age` - Age of audio segment (seconds)

**Example CSV Row:**
```csv
2026-04-25T14:32:15,County Dispatch,Ten four,10-4 [Acknowledged],10-4,,,,0.015,mlx-community/parakeet-tdt-0.6b-v3,1.2
```

### Transcript Format

**Main Transcript (scanner-feed.txt):**
```
[2026-04-25 14:32:15] County Dispatch: 10-4 [Acknowledged]
[2026-04-25 14:32:18] County Dispatch: Unit 201 responding to 123 Main St
```

**Raw Audit Log (scanner-feed.raw.txt):**
```
[2026-04-25 14:32:15] normalized: 10-4 [Acknowledged]
[2026-04-25 14:32:15] raw: Ten four.
```

## Python Usage Examples

### Basic Usage

```python
import scanner_app.app as scanner
import scanner_app.config as config
import scanner_app.feeds as feeds

# Load configuration
cfg = config.load_config()

# Load audio feeds
feed_list = feeds.load_feeds(cfg['FEEDS_FILE'])

# Start scanner
scanner.main()
```

### Transcribe Audio

```python
import scanner_app.asr as asr

# Connect to ASR server
asr.connect_asr_server('http://127.0.0.1:18765')

# Transcribe audio file
result = asr.transcribe_audio('/path/to/audio.wav')
print(f"Transcription: {result['transcription']}")
print(f"Confidence: {result['confidence']}")
```

### Process Audio Feed

```python
import scanner_app.audio as audio

# Connect to audio feed
stream = audio.connect_audio_feed('https://broadcastify.cdnstream1.com/31880')

# Process audio segments
for segment in audio.segment_audio(stream):
    # Transcribe segment
    transcription = asr.transcribe_audio(segment)
    
    # Normalize text
    normalized = scanner_app.lexicon.normalize_text(transcription)
    
    # Write to output
    scanner_app.csv_log.write_csv_event({
        'timestamp': datetime.now(),
        'raw_text': transcription,
        'normalized_text': normalized
    })
```

### Normalization Examples

```python
import scanner_app.lexicon as lexicon

# Normalize text
text = "ten four"
normalized = lexicon.normalize_text(text)
# Result: "10-4 [Acknowledged]"

# Expand radio codes
text = "10-4"
expanded = lexicon.expand_radio_codes(text)
# Result: "10-4 [Acknowledged]"

# Normalize radio units
text = "unit two zero one"
normalized = lexicon.normalize_radio_units(text)
# Result: "unit 201"

# Detect HAM callsigns
text = "KJ Five INP"
callsigns = lexicon.detect_ham_callsigns(text)
# Result: ["KJ5INP"]
```

## Error Handling

### Common Errors

**Parakeet Server Not Responding:**
```python
try:
    result = asr.transcribe_audio(audio_path)
except ConnectionError:
    print("Parakeet server not available")
    # Retry or fallback
```

**Audio Feed Connection Failed:**
```python
try:
    stream = audio.connect_audio_feed(url)
except Exception as e:
    print(f"Failed to connect to feed: {e}")
    # Try alternative feed
```

**Transcription Timeout:**
```python
import time

start_time = time.time()
while time.time() - start_time < 30:  # 30 second timeout
    try:
        result = asr.transcribe_audio(audio_path)
        break
    except TimeoutError:
        continue
```

## Performance Optimization

### Batch Processing

```python
# Process multiple segments efficiently
segments = collect_audio_segments()
for segment in segments:
    result = asr.transcribe_audio(segment)
    # Process result
```

### Caching

```python
# Cache normalization results
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_normalize(text):
    return lexicon.normalize_text(text)
```

### Connection Pooling

```python
# Reuse ASR server connection
asr.connect_asr_server('http://127.0.0.1:18765')
# Reuse connection for multiple transcriptions
```

## Testing

### Unit Tests

```python
import unittest
import scanner_app.lexicon as lexicon

class TestNormalization(unittest.TestCase):
    def test_radio_codes(self):
        result = lexicon.normalize_text("ten four")
        self.assertEqual(result, "10-4 [Acknowledged]")
    
    def test_ham_callsigns(self):
        result = lexicon.detect_ham_callsigns("KJ Five INP")
        self.assertEqual(result, ["KJ5INP"])

if __name__ == '__main__':
    unittest.main()
```

### Integration Tests

```python
def test_full_pipeline():
    # Test audio feed connection
    stream = audio.connect_audio_feed(TEST_FEED_URL)
    assert stream is not None
    
    # Test transcription
    result = asr.transcribe_audio(TEST_AUDIO_FILE)
    assert result['transcription'] is not None
    
    # Test normalization
    normalized = lexicon.normalize_text(result['transcription'])
    assert len(normalized) > 0
```

## Next Steps

- **Setup:** See [Setup](./setup.md) for installation instructions
- **Running:** See [Running](./running.md) for operation guide
- **Architecture:** See [Architecture](./architecture.md) for system design
- **Troubleshooting:** See [Troubleshooting](./troubleshooting.md) for common issues
