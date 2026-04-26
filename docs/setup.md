# Setup Guide

This guide walks you through setting up the scanner feed transcription system for the first time.

## Step 1: Clone or Download the Project

### Option A: Clone with Git
```bash
cd ~/Developer/Github
git clone https://github.com/TheSethRose/scanner-feed.git
cd scanner-feed
```

### Option B: Download ZIP
1. Download the project ZIP from GitHub
2. Extract to `~/Developer/Github/scanner-feed`
3. Open Terminal and navigate to the folder:
```bash
cd ~/Developer/Github/scanner-feed
```

## Step 2: Install Python Dependencies

### Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Required Packages
```bash
pip install -U parakeet-mlx numpy soundfile
```

**Note:** The first time you run this, it will download the MLX model (approximately 1-2GB). This happens automatically when you first start the Parakeet server.

## Step 3: Configure Audio Feeds

### Understanding feeds.txt
The `feeds.txt` file contains one audio feed per line in the format:
```
Name|URL
```

### Default feeds.txt
The project includes a sample `feeds.txt` file. Check its contents:
```bash
cat feeds.txt
```

### How to Update feeds.txt for the Container

**Important:** The Docker container needs access to the `feeds.txt` file. The container mounts the project folder, so any changes to `feeds.txt` are immediately available.

#### Option 1: Edit feeds.txt directly
```bash
# Open in your preferred editor
nano feeds.txt
# or
code feeds.txt  # VS Code
# or
open -a "TextEdit" feeds.txt
```

#### Option 2: Add a new feed
```bash
# Append a new feed (example)
echo "My Local Scanner|https://broadcastify.cdnstream1.com/31880" >> feeds.txt
```

#### Option 3: Replace all feeds
```bash
# Create a new feeds.txt with your feeds
cat > feeds.txt << 'EOF'
My County Dispatch|https://broadcastify.cdnstream1.com/31880
My Fire Department|https://broadcastify.cdnstream1.com/12345
My Police Department|https://broadcastify.cdnstream1.com/67890
EOF
```

### Example feeds.txt Content
```
County Dispatch|https://broadcastify.cdnstream1.com/31880
Fire Department|https://broadcastify.cdnstream1.com/12345
Police Department|https://broadcastify.cdnstream1.com/67890
```

### Testing Your Feeds
Before starting the system, test that your feeds are accessible:
```bash
# Test a single feed URL
curl -I "https://broadcastify.cdnstream1.com/31880"
```

## Step 4: Start the Native Parakeet Server

### Option A: Manual Start (for testing)
```bash
# Activate virtual environment if not already active
source .venv/bin/activate

# Start the Parakeet server
PARAKEET_SERVER_PORT=18765 python parakeet_server.py
```

The server will download the MLX model on first run (1-2GB). Subsequent starts will be faster.

### Option B: Launchd Service (recommended for production)
```bash
# Copy the launchd plist to your LaunchAgents folder
cp launchd/com.scanner-feed.parakeet.plist ~/Library/LaunchAgents/

# Load and start the service
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.scanner-feed.parakeet.plist
launchctl kickstart -k "gui/$(id -u)/com.scanner-feed.parakeet"
```

### Verify Parakeet Server
```bash
curl http://127.0.0.1:18765/health
```

Expected response:
```json
{"status": "ok", "model": "mlx-community/parakeet-tdt-0.6b-v3"}
```

## Step 5: Start the Docker Worker

### Build and Start the Container
```bash
docker compose up -d --build
```

This will:
1. Build the Docker image for the scanner worker
2. Start the container in detached mode
3. Mount the project folders for logs and runtime data

### Verify Docker Worker
```bash
curl http://127.0.0.1:49173/health
```

Expected response:
```json
{"status": "ok", "container": "scanner-feed-worker"}
```

### Check Container Status
```bash
docker compose ps
```

Expected output:
```
NAME                COMMAND                  SERVICE   STATUS
scanner-feed-worker "python -m scanner_a…"   scanner   Up (healthy)
```

## Step 6: Verify the Setup

### Check All Health Endpoints
```bash
# Parakeet server (native MLX)
curl http://127.0.0.1:18765/health

# Docker worker
curl http://127.0.0.1:49173/health
```

### Check Logs Directory
```bash
ls -la /Users/sethrose/Developer/Github/scanner-feed/logs/
```

### Check Runtime Directory
```bash
ls -la /Users/sethrose/Developer/Github/scanner-feed/runtime/
```

## Step 7: Monitor Transcription

### View Live Transcript
```bash
tail -f /Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.txt
```

### View Docker Logs
```bash
docker compose logs -f scanner
```

### View CSV Event Logs
```bash
# List all CSV logs
ls -la /Users/sethrose/Developer/Github/scanner-feed/logs/

# View today's log
tail -f /Users/sethrose/Developer/Github/scanner-feed/logs/scanner-events-*.csv
```

## Configuration Files

### Environment Variables
The system uses these environment variables (set in `docker-compose.yml`):

| Variable | Default | Description |
|----------|---------|-------------|
| `FEEDS_FILE` | `/app/feeds.txt` | File containing audio feeds |
| `WORKDIR` | `/Users/sethrose/Developer/Github/scanner-feed/runtime/segments` | Temp chunk directory |
| `LOG_DIR` | `/Users/sethrose/Developer/Github/scanner-feed/logs` | CSV event logs |
| `OUTFILE` | `/Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.txt` | Transcript output |
| `RAW_OUTFILE` | `/Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.raw.txt` | Audit log |
| `HEALTH_PORT` | `49173` | Worker health endpoint port |

### Customizing Configuration
To customize settings, edit the `docker-compose.yml` file and restart the container:
```bash
docker compose down
docker compose up -d --build
```

## Troubleshooting Setup Issues

If you encounter issues during setup, see [Troubleshooting](./troubleshooting.md).

## Next Steps

- **Running the System**: See [Running](./running.md)
- **Understanding Data**: See [Data & Logs](./data-logs.md)
- **Troubleshooting**: See [Troubleshooting](./troubleshooting.md)
