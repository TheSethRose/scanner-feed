# Architecture

This guide explains how the scanner feed transcription system works, from audio input to transcript output.

## System Overview

The scanner feed transcription system consists of two main components:

1. **Native MLX Parakeet Server** - Runs on macOS using MLX/Metal for GPU acceleration
2. **Docker Worker** - Containerized scanner worker that processes audio feeds

```
┌─────────────────────────────────────────────────────────────────┐
│                        macOS Host                               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         Native MLX Parakeet Server (port 18765)         │   │
│  │  • MLX/Metal GPU acceleration                           │   │
│  │  • NVIDIA Parakeet ASR model                            │   │
│  │  • Audio segmentation and transcription                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              │ HTTP API                         │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         Docker Worker Container (port 49173)            │   │
│  │  • Audio feed connection                                │   │
│  │  • Audio preprocessing                                  │   │
│  │  • Segment management                                   │   │
│  │  • CSV logging                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Output Files                          │   │
│  │  • scanner-feed.txt (transcript)                        │   │
│  │  • scanner-feed.raw.txt (audit log)                     │   │
│  │  • logs/scanner-events-*.csv (daily logs)               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Native MLX Parakeet Server

**Location:** `parakeet_server.py`

**Purpose:** Provides NVIDIA Parakeet ASR (Automatic Speech Recognition) via MLX on macOS.

**Key Features:**
- Uses MLX/Metal for GPU acceleration on Apple Silicon
- Accepts audio segments via HTTP API
- Returns transcriptions in JSON format
- Runs as a native macOS process (not in Docker)

**HTTP API Endpoints:**
- `POST /transcribe` - Transcribe an audio file
- `GET /health` - Health check endpoint

**Why Native?**
- MLX requires direct access to Apple Silicon GPU
- Docker containers can't access MLX/Metal efficiently
- Native execution provides best performance

### 2. Docker Worker

**Location:** `Dockerfile`, `docker-compose.yml`

**Purpose:** Connects to audio feeds, processes audio, and manages transcription workflow.

**Key Features:**
- Connects to multiple audio feeds simultaneously
- Preprocesses audio (filters, segmentation)
- Manages transcription queue
- Writes CSV logs and transcripts
- Provides health monitoring

**Container Configuration:**
- **Image:** Built from `Dockerfile`
- **Ports:** 49173 (health endpoint)
- **Volumes:** Mounts project folders for logs and runtime data
- **Environment:** Configured via `docker-compose.yml`

### 3. Audio Feed Management

**Configuration:** `feeds.txt`

**Format:** `Name|URL` (one per line)

**Supported Sources:**
- Broadcastify streams
- Any HTTP/HTTPS audio stream (MP3, AAC, etc.)

**Feed Processing:**
1. Worker reads `feeds.txt` on startup
2. Connects to each audio stream
3. Continuously monitors for audio
4. Segments audio when speech is detected

### 4. Audio Processing Pipeline

```
Audio Stream → Preprocessing → Segmentation → Transcription → Output
```

**Step 1: Audio Preprocessing**
- FFmpeg filter chain for voice-band cleanup
- Sample rate conversion
- Channel normalization

**Step 2: Segmentation**
- Voice Activity Detection (VAD)
- Silence detection
- Segment boundaries based on speech patterns

**Step 3: Transcription**
- Audio segments sent to Parakeet server
- MLX model performs ASR
- Returns text transcription

**Step 4: Normalization**
- Radio code normalization (e.g., "ten four" → "10-4 [Acknowledged]")
- Radio unit normalization
- Phonetic spelling normalization
- HAM callsign detection
- Weather alert detection

### 5. Output Generation

**Transcript Output:**
- `scanner-feed.txt` - Clean, normalized text
- `scanner-feed.raw.txt` - Raw and normalized text for audit

**CSV Event Logs:**
- Daily files: `scanner-events-YYYY-MM-DD.csv`
- Contains detailed event data
- Includes raw/normalized text, codes, units, weather, RMS levels

**Temporary Files:**
- `runtime/segments/` - Audio segments before transcription
- Automatically cleaned up based on retention settings

## Data Flow

### 1. Startup Sequence
```
1. Launch Parakeet server (native MLX)
2. Start Docker worker container
3. Worker connects to audio feeds
4. Worker establishes connection to Parakeet server
5. System begins processing audio
```

### 2. Audio Processing Loop
```
1. Worker monitors audio feeds
2. Detects speech using VAD
3. Segments audio when speech starts
4. Waits for silence to end segment
5. Sends segment to Parakeet server
6. Receives transcription
7. Normalizes text
8. Writes to output files
9. Logs to CSV
```

### 3. Normalization Pipeline
```
Raw Transcription → HAM Callsigns → Phonetic Spelling → Radio Units → Scanner Codes → Radio Numbers → Final Output
```

**Examples:**
- `KJ Five INP` → `KJ5INP`
- `ten four` → `10-4 [Acknowledged]`
- `seventy one seventy two` → `seventy one seventy two [71 72]`
- `received twenty thirty eight` → `received twenty thirty eight [20:38]`

### 4. Weather Alert Detection
```
WX-1: rotation, hail, storm damage
WX-2: tornado watch, funnel cloud, severe thunderstorm warning
WX-3: tornado warning, confirmed tornado
WX-4: tornado emergency, take shelter, debris signature
```

Weather terms are highlighted in terminal output only (not in transcript files).

## Configuration

### Environment Variables

**Parakeet Server:**
- `PARAKEET_SERVER_PORT` - Server port (default: 18765)
- `PARAKEET_MODEL` - MLX model to load

**Docker Worker:**
- `ASR_SERVER_URL` - Parakeet server URL
- `FEEDS_FILE` - Audio feeds configuration file
- `WORKDIR` - Temporary segment directory
- `LOG_DIR` - CSV log directory
- `OUTFILE` - Transcript output file
- `RAW_OUTFILE` - Raw audit log file
- `HEALTH_PORT` - Health endpoint port

**Audio Processing:**
- `MIN_RMS` - Minimum audio level (0.0015)
- `START_SPEECH_SECONDS` - Speech detection threshold (0.5s)
- `END_SILENCE_SECONDS` - Silence threshold (0.9s)
- `MIN_SEGMENT_SECONDS` - Minimum segment length (1.0s)
- `MAX_SEGMENT_SECONDS` - Maximum segment length (18s)

**Log Management:**
- `CSV_RETENTION_DAYS` - Log retention (14 days)
- `CSV_MAX_TOTAL_MB` - Max log size (500MB)
- `COMPRESS_OLD_CSV_DAYS` - Compression threshold (2 days)

## Performance Characteristics

### Resource Usage
- **CPU:** Moderate (MLX uses GPU, worker uses CPU for audio processing)
- **Memory:** 2-4GB (MLX model + audio buffers)
- **Disk:** Growing (logs and transcripts)
- **Network:** Continuous (audio stream + API calls)

### Latency
- **Audio to Transcript:** ~1-3 seconds (depends on segment length)
- **Parakeet Processing:** ~0.5-1 second per segment
- **Total Pipeline:** ~1.5-4 seconds

### Scalability
- **Feeds:** Supports multiple simultaneous feeds (tested up to 5)
- **Concurrent Processing:** Single transcription at a time (sequential)
- **Storage:** Daily CSV logs, continuous transcript append

## Monitoring

### Health Endpoints
- **Parakeet Server:** `http://127.0.0.1:18765/health`
- **Docker Worker:** `http://127.0.0.1:49173/health`

### Metrics
- Transcription count
- Audio level (RMS)
- Segment age
- Queue depth
- Error rates

### Logs
- **Docker logs:** Real-time processing status
- **CSV logs:** Detailed event data
- **Transcript files:** Clean output

## Security Considerations

### Network Security
- Audio feeds use HTTPS (encrypted)
- Local API endpoints (no external access)
- Docker container isolation

### Data Privacy
- Transcripts stored locally
- No external data transmission
- Configurable retention policies

### Access Control
- Local-only access to health endpoints
- Docker container network isolation
- File system permissions

## Troubleshooting Architecture Issues

### Parakeet Server Issues
- Check MLX/Metal compatibility
- Verify model download
- Check port availability

### Docker Worker Issues
- Check container health
- Verify network connectivity
- Check resource limits

### Audio Processing Issues
- Verify feed URLs
- Check audio quality
- Adjust processing parameters

## Next Steps

- **Setup:** See [Setup](./setup.md) for installation instructions
- **Running:** See [Running](./running.md) for operation guide
- **Troubleshooting:** See [Troubleshooting](./troubleshooting.md) for common issues
