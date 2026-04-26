# Running the System

This guide explains how to start, monitor, and stop the scanner feed transcription system.

## Starting the System

### Complete Startup Sequence

#### 1. Start the Native Parakeet Server
```bash
# Option A: Manual start (for testing)
source .venv/bin/activate
PARAKEET_SERVER_PORT=18765 python parakeet_server.py

# Option B: Launchd service (recommended for production)
launchctl kickstart -k "gui/$(id -u)/com.scanner-feed.parakeet"
```

#### 2. Start the Docker Worker
```bash
docker compose up -d
```

### Quick Start Script
Create a startup script for convenience:

```bash
# Create start script
cat > start-scanner.sh << 'EOF'
#!/bin/bash
echo "Starting Scanner Feed Transcription System..."

# Start Parakeet server
echo "Starting Parakeet server..."
launchctl kickstart -k "gui/$(id -u)/com.scanner-feed.parakeet"

# Wait a moment for server to start
sleep 5

# Start Docker worker
echo "Starting Docker worker..."
docker compose up -d

# Check status
echo "Checking status..."
curl -s http://127.0.0.1:18765/health | jq .
curl -s http://127.0.0.1:49173/health | jq .

echo "System started!"
EOF

chmod +x start-scanner.sh
```

## Monitoring the System

### Check System Status
```bash
# Check Parakeet server health
curl http://127.0.0.1:18765/health

# Check Docker worker health
curl http://127.0.0.1:49173/health

# Check Docker container status
docker compose ps
```

### Monitor Live Transcription
```bash
# Watch the main transcript file
tail -f /Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.txt

# Watch the raw audit log
tail -f /Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.raw.txt

# Watch Docker logs in real-time
docker compose logs -f scanner
```

### Monitor CSV Event Logs
```bash
# List all CSV logs
ls -lh /Users/sethrose/Developer/Github/scanner-feed/logs/

# Watch today's CSV log
tail -f /Users/sethrose/Developer/Github/scanner-feed/logs/scanner-events-*.csv

# Count lines in today's log
wc -l /Users/sethrose/Developer/Github/scanner-feed/logs/scanner-events-*.csv
```

### Monitor System Resources
```bash
# Check Docker container resource usage
docker stats scanner-feed-worker

# Check disk usage for logs and runtime
du -sh /Users/sethrose/Developer/Github/scanner-feed/logs/
du -sh /Users/sethrose/Developer/Github/scanner-feed/runtime/
```

## Stopping the System

### Stop Docker Worker Only
```bash
docker compose down
```

### Stop Parakeet Server (if running manually)
```bash
# If running in terminal, press Ctrl+C
# If using launchd:
launchctl bootout "gui/$(id -u)/com.scanner-feed.parakeet"
```

### Stop Everything
```bash
# Stop Docker worker
docker compose down

# Stop Parakeet service
launchctl bootout "gui/$(id -u)/com.scanner-feed.parakeet"

# Verify everything is stopped
docker compose ps
curl http://127.0.0.1:18765/health  # Should fail
curl http://127.0.0.1:49173/health  # Should fail
```

## Restarting the System

### Full Restart
```bash
# Stop everything
docker compose down
launchctl bootout "gui/$(id -u)/com.scanner-feed.parakeet"

# Wait a moment
sleep 2

# Start everything
launchctl kickstart -k "gui/$(id -u)/com.scanner-feed.parakeet"
sleep 5
docker compose up -d
```

### Restart Docker Worker Only
```bash
docker compose restart scanner
```

### Restart Parakeet Server Only
```bash
launchctl bootout "gui/$(id -u)/com.scanner-feed.parakeet"
sleep 2
launchctl kickstart -k "gui/$(id -u)/com.scanner-feed.parakeet"
```

## Updating Feeds While Running

You can update `feeds.txt` while the system is running. The Docker worker will automatically pick up changes:

```bash
# Add a new feed
echo "New Feed Name|https://broadcastify.cdnstream1.com/12345" >> feeds.txt

# The worker will automatically reload the feeds file
# Check Docker logs to see the reload
docker compose logs -f scanner | grep "feeds"
```

## Checking Logs

### View Recent Transcripts
```bash
# Last 50 lines of transcript
tail -n 50 /Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.txt

# Last 50 lines of raw audit log
tail -n 50 /Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.raw.txt
```

### View CSV Logs
```bash
# Today's CSV log
ls -t /Users/sethrose/Developer/Github/scanner-feed/logs/scanner-events-*.csv | head -1

# View with headers
head -1 $(ls -t /Users/sethrose/Developer/Github/scanner-feed/logs/scanner-events-*.csv | head -1)
```

### Search Transcripts
```bash
# Search for specific text in transcripts
grep -i "fire" /Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.txt

# Search in CSV logs
grep -i "10-4" /Users/sethrose/Developer/Github/scanner-feed/logs/scanner-events-*.csv
```

## Performance Monitoring

### Check Processing Status
```bash
# Check if audio is being processed
docker compose logs -f scanner | grep "segment"

# Check transcription queue
docker compose logs -f scanner | grep "queue"
```

### Monitor Audio Levels
```bash
# Check Docker logs for audio level warnings
docker compose logs -f scanner | grep -i "rms\|audio\|level"
```

## Common Operations

### View System Information
```bash
# System status summary
echo "=== Parakeet Server ==="
curl -s http://127.0.0.1:18765/health | python3 -m json.tool

echo -e "\n=== Docker Worker ==="
curl -s http://127.0.0.1:49173/health | python3 -m json.tool

echo -e "\n=== Container Status ==="
docker compose ps

echo -e "\n=== Log Files ==="
ls -lh /Users/sethrose/Developer/Github/scanner-feed/logs/ | tail -5

echo -e "\n=== Transcript Files ==="
ls -lh /Users/sethrose/Developer/Github/scanner-feed/runtime/*.txt
```

### Check Disk Usage
```bash
# Overall disk usage
du -sh /Users/sethrose/Developer/Github/scanner-feed/*

# Log directory
du -sh /Users/sethrose/Developer/Github/scanner-feed/logs/

# Runtime directory
du -sh /Users/sethrose/Developer/Github/scanner-feed/runtime/
```

## Next Steps

- **Troubleshooting**: See [Troubleshooting](./troubleshooting.md) if you encounter issues
- **Data & Logs**: See [Data & Logs](./data-logs.md) to understand the output files
- **Architecture**: See [Architecture](./architecture.md) to understand how the system works
