#!/bin/bash
# System Status Script
# Run this to check the health of the scanner feed transcription system

echo "=== Scanner Feed System Status ==="
echo "Date: $(date)"
echo ""

# Check Parakeet Server
echo "1. Parakeet Server (Native MLX)"
echo "-------------------------------"
if curl -s http://127.0.0.1:18765/health > /dev/null 2>&1; then
    curl -s http://127.0.0.1:18765/health | python3 -m json.tool 2>/dev/null || echo "Status: OK (JSON parse failed)"
else
    echo "Status: NOT RESPONDING"
    echo "Action: Start Parakeet server with: launchctl kickstart -k \"gui/\$(id -u)/com.scanner-feed.parakeet\""
fi
echo ""

# Check Docker Worker
echo "2. Docker Worker"
echo "----------------"
if curl -s http://127.0.0.1:49173/health > /dev/null 2>&1; then
    curl -s http://127.0.0.1:49173/health | python3 -m json.tool 2>/dev/null || echo "Status: OK (JSON parse failed)"
else
    echo "Status: NOT RESPONDING"
    echo "Action: Start Docker worker with: docker compose up -d"
fi
echo ""

# Check Docker Container Status
echo "3. Docker Container Status"
echo "--------------------------"
docker compose ps 2>/dev/null || echo "Docker compose not available"
echo ""

# Check Recent Errors
echo "4. Recent Errors (last 20 lines)"
echo "---------------------------------"
docker compose logs --tail 20 scanner 2>/dev/null | grep -i error || echo "No errors found"
echo ""

# Check Disk Space
echo "5. Disk Space"
echo "-------------"
df -h /Users/sethrose/Developer/Github/scanner-feed/ 2>/dev/null || echo "Cannot check disk space"
echo ""

# Check Log Files
echo "6. Log Files"
echo "------------"
echo "CSV Logs:"
ls -lh /Users/sethrose/Developer/Github/scanner-feed/logs/*.csv 2>/dev/null | tail -5 || echo "No CSV logs found"
echo ""
echo "Transcript Files:"
ls -lh /Users/sethrose/Developer/Github/scanner-feed/runtime/*.txt 2>/dev/null || echo "No transcript files found"
echo ""

# Check Audio Feeds
echo "7. Audio Feeds Configuration"
echo "----------------------------"
if [ -f "/Users/sethrose/Developer/Github/scanner-feed/feeds.txt" ]; then
    echo "Feeds configured: $(wc -l < /Users/sethrose/Developer/Github/scanner-feed/feeds.txt)"
    head -n 3 /Users/sethrose/Developer/Github/scanner-feed/feeds.txt
    if [ $(wc -l < /Users/sethrose/Developer/Github/scanner-feed/feeds.txt) -gt 3 ]; then
        echo "... and more"
    fi
else
    echo "feeds.txt not found"
fi
echo ""

# Check Launchd Service
echo "8. Launchd Service Status"
echo "-------------------------"
launchctl list | grep scanner-feed || echo "Launchd service not found"
echo ""

echo "=== Status Check Complete ==="
echo ""
echo "If any components are not responding, see the Troubleshooting guide."
