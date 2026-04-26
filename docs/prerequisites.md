# Prerequisites

Before setting up the scanner feed transcription system, ensure you have the following:

## System Requirements

### Hardware
- **Mac with Apple Silicon (M1/M2/M3)** - Required for MLX GPU acceleration
- **Minimum 8GB RAM** - Recommended for smooth operation
- **Storage** - At least 2GB free space for logs and temporary files

### Software
- **macOS 12.0+** - Monterey or later
- **Docker Desktop** - For running the scanner worker container
- **Homebrew** - For installing dependencies

## Required Dependencies

### 1. Docker Desktop
```bash
# Install Docker Desktop from https://www.docker.com/products/docker-desktop/
# Or via Homebrew:
brew install --cask docker
```

### 2. FFmpeg
```bash
brew install ffmpeg
```

### 3. Python 3.11+
```bash
# Check if Python 3.11+ is installed
python3 --version

# If not installed, use Homebrew:
brew install python@3.11
```

### 4. Git (optional, for cloning)
```bash
brew install git
```

## Network Requirements

- **Internet connection** - Required for:
  - Downloading MLX models
  - Streaming audio from Broadcastify or other sources
  - Docker image pulls

- **Firewall permissions** - Ensure Docker and Python can access:
  - Audio stream URLs (typically port 443 for HTTPS)
  - Local ports 18765 (Parakeet server) and 49173 (worker health)

## Audio Source Requirements

### Broadcastify Feeds
- Valid Broadcastify account may be required for some feeds
- Feed URLs typically follow this format: `https://broadcastify.cdnstream1.com/XXXXX`

### Custom Feeds
- Any HTTP/HTTPS audio stream URL (MP3, AAC, etc.)
- Must be accessible from your network

## Verification Checklist

Before proceeding, verify:

- [ ] Docker Desktop is running
- [ ] FFmpeg is installed: `ffmpeg -version`
- [ ] Python 3.11+ is available: `python3 --version`
- [ ] Homebrew is installed: `brew --version`
- [ ] Internet connection is active
- [ ] At least 2GB free disk space

## Next Steps

Once prerequisites are met, proceed to [Setup](./setup.md) to install and configure the system.
