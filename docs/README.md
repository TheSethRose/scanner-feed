# Scanner Feed Documentation

This documentation helps first-time users set up and run the scanner feed transcription system.

## Quick Start

1. **Prerequisites** - What you need before starting
2. **Setup** - Installation and configuration
3. **Running** - How to start the system
4. **Data & Logs** - Where to find information
5. **Troubleshooting** - Common issues and solutions
6. **Architecture** - How the system works

## System Overview

The scanner feed transcription system uses NVIDIA Parakeet via MLX to transcribe live audio feeds from scanners. It consists of:

- **Native MLX Parakeet Server** - Runs on macOS using MLX/Metal for GPU acceleration
- **Docker Worker** - Containerized scanner worker that processes audio feeds
- **CSV Logging** - Daily event logs with detailed transcription data
- **Transcript Output** - Clean text transcripts of scanner communications

## Getting Help

- **First-time users**: Start with [Prerequisites](./prerequisites.md) and [Setup](./setup.md)
- **Troubleshooting**: Check [Troubleshooting](./troubleshooting.md)
- **Architecture details**: See [Architecture](./architecture.md)
- **API/Developer docs**: See [API Reference](./api-reference.md)

## Quick Commands

```bash
# Check system status
curl http://127.0.0.1:18765/health  # Parakeet server
curl http://127.0.0.1:49173/health  # Docker worker

# View logs
tail -f /Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.txt
docker compose logs -f scanner

# Check CSV logs
ls -la /Users/sethrose/Developer/Github/scanner-feed/logs/
```
