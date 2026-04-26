# Scanner Feed Transcription

Live transcription of scanner audio feeds using NVIDIA Parakeet via MLX.

## Documentation

Comprehensive documentation is available in the [`docs/`](./docs/) folder:

- **[Prerequisites](./docs/prerequisites.md)** - What you need before starting
- **[Setup Guide](./docs/setup.md)** - Installation and configuration
- **[Running the System](./docs/running.md)** - How to start, monitor, and stop
- **[Data & Logs](./docs/data-logs.md)** - Where to find output files
- **[Troubleshooting](./docs/troubleshooting.md)** - Common issues and solutions
- **[Architecture](./docs/architecture.md)** - How the system works
- **[API Reference](./docs/api-reference.md)** - Developer and API documentation

## Quick Start

### Prerequisites
- macOS 12.0+ with Apple Silicon (M1/M2/M3)
- Docker Desktop
- Homebrew

### Install
```bash
brew install ffmpeg
python3 -m venv .venv
source .venv/bin/activate
pip install -U parakeet-mlx numpy soundfile
```

### Start System
```bash
# Start Parakeet server (native MLX)
launchctl kickstart -k "gui/$(id -u)/com.scanner-feed.parakeet"

# Start Docker worker
docker compose up -d
```

### Check Status
```bash
curl http://127.0.0.1:18765/health  # Parakeet server
curl http://127.0.0.1:49173/health  # Docker worker
```

### View Transcripts
```bash
tail -f /Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.txt
```

## Run (Legacy)
```bash
python scanner.py
```

## Configuration

See [`docs/api-reference.md`](./docs/api-reference.md) for complete configuration options and environment variables.

## Quick Reference

### System Status
```bash
# Check Parakeet server
curl http://127.0.0.1:18765/health

# Check Docker worker
curl http://127.0.0.1:49173/health

# View Docker logs
docker compose logs -f scanner
```

### Data Locations
- **Transcripts:** `/Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.txt`
- **Raw audit log:** `/Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.raw.txt`
- **CSV logs:** `/Users/sethrose/Developer/Github/scanner-feed/logs/`
- **Audio feeds:** `/Users/sethrose/Developer/Github/scanner-feed/feeds.txt`

### Normalization Examples
```
KJ Five INP → KJ5INP
ten four → 10-4 [Acknowledged]
seventy one seventy two → seventy one seventy two [71 72]
```

### Weather Alerts (terminal only)
```
WX-1: rotation, hail, storm damage
WX-2: tornado watch, funnel cloud, severe thunderstorm warning
WX-3: tornado warning, confirmed tornado
WX-4: tornado emergency, take shelter, debris signature
```
