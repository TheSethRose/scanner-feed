# Troubleshooting

This guide helps you diagnose and fix common issues with the scanner feed transcription system.

## Quick Diagnostic Commands

Run these commands first to identify the problem:

```bash
# Check all health endpoints
echo "=== Parakeet Server ==="
curl -s http://127.0.0.1:18765/health | python3 -m json.tool 2>/dev/null || echo "Parakeet server not responding"

echo -e "\n=== Docker Worker ==="
curl -s http://127.0.0.1:49173/health | python3 -m json.tool 2>/dev/null || echo "Docker worker not responding"

echo -e "\n=== Docker Container Status ==="
docker compose ps

echo -e "\n=== Recent Errors ==="
docker compose logs --tail 50 scanner | grep -i error

echo -e "\n=== Disk Space ==="
df -h /Users/sethrose/Developer/Github/scanner-feed/
```

## Common Issues and Solutions

### Issue 1: Parakeet Server Won't Start

**Symptoms:**
- `curl http://127.0.0.1:18765/health` fails
- "Connection refused" error
- Server process not running

**Solutions:**

1. **Check if server is running:**
   ```bash
   ps aux | grep parakeet_server.py
   ```

2. **Start the server manually:**
   ```bash
   source .venv/bin/activate
   PARAKEET_SERVER_PORT=18765 python parakeet_server.py
   ```

3. **Check for port conflicts:**
   ```bash
   lsof -i :18765
   ```

4. **Check launchd service status:**
   ```bash
   launchctl list | grep scanner-feed
   ```

5. **Restart launchd service:**
   ```bash
   launchctl bootout "gui/$(id -u)/com.scanner-feed.parakeet"
   sleep 2
   launchctl kickstart -k "gui/$(id -u)/com.scanner-feed.parakeet"
   ```

6. **Check for MLX model download issues:**
   ```bash
   # Check if model is downloading
   ls -lh ~/.cache/huggingface/hub/
   ```

### Issue 2: Docker Worker Won't Start

**Symptoms:**
- `curl http://127.0.0.1:49173/health` fails
- Container not running or unhealthy
- Docker compose errors

**Solutions:**

1. **Check Docker Desktop is running:**
   ```bash
   docker info
   ```

2. **Check container status:**
   ```bash
   docker compose ps
   ```

3. **View container logs:**
   ```bash
   docker compose logs scanner
   ```

4. **Rebuild and restart:**
   ```bash
   docker compose down
   docker compose up -d --build
   ```

5. **Check for port conflicts:**
   ```bash
   lsof -i :49173
   ```

6. **Check Docker resources:**
   ```bash
   docker system df
   docker stats
   ```

### Issue 3: No Transcription Output

**Symptoms:**
- Transcript files are empty or not updating
- No audio being processed

**Solutions:**

1. **Check audio feeds configuration:**
   ```bash
   cat feeds.txt
   ```

2. **Test feed URLs:**
   ```bash
   # Test a feed URL
   curl -I "https://broadcastify.cdnstream1.com/31880"
   ```

3. **Check Docker logs for feed connection issues:**
   ```bash
   docker compose logs -f scanner | grep -i "feed\|connection\|stream"
   ```

4. **Verify audio is being received:**
   ```bash
   docker compose logs -f scanner | grep -i "audio\|segment\|rms"
   ```

5. **Check minimum audio level setting:**
   - If audio is too quiet, increase `MIN_RMS` in `docker-compose.yml`
   - Default is `0.0015`, try `0.0005` for quieter feeds

6. **Check transcription queue:**
   ```bash
   docker compose logs -f scanner | grep -i "queue\|transcribe"
   ```

### Issue 4: Poor Transcription Quality

**Symptoms:**
- Transcriptions are inaccurate or incomplete
- Missing words or phrases

**Solutions:**

1. **Check audio quality:**
   ```bash
   docker compose logs -f scanner | grep -i "rms\|audio\|level"
   ```

2. **Adjust audio processing settings:**
   - Lower `MIN_RMS` if quiet audio is being skipped
   - Increase `START_SPEECH_SECONDS` if speech is cut off
   - Decrease `END_SILENCE_SECONDS` if segments are too long

3. **Check feed URL quality:**
   - Some feeds may have poor audio quality
   - Try different feeds from feeds.txt

4. **Verify MLX model is loaded:**
   ```bash
   curl http://127.0.0.1:18765/health
   ```

### Issue 5: Docker Container Keeps Restarting

**Symptoms:**
- Container shows "Restarting" status
- Logs show repeated restarts

**Solutions:**

1. **Check container logs:**
   ```bash
   docker compose logs --tail 100 scanner
   ```

2. **Check health check failures:**
   ```bash
   docker inspect scanner-feed-worker | grep -A 10 "Health"
   ```

3. **Disable health check temporarily:**
   Edit `docker-compose.yml` and comment out the `healthcheck` section, then restart.

4. **Check resource limits:**
   ```bash
   docker stats scanner-feed-worker
   ```

### Issue 6: Permission Errors

**Symptoms:**
- "Permission denied" errors in logs
- Can't write to log or runtime directories

**Solutions:**

1. **Check directory permissions:**
   ```bash
   ls -la /Users/sethrose/Developer/Github/scanner-feed/
   ```

2. **Fix permissions:**
   ```bash
   chmod -R 755 /Users/sethrose/Developer/Github/scanner-feed/logs/
   chmod -R 755 /Users/sethrose/Developer/Github/scanner-feed/runtime/
   ```

3. **Check Docker volume permissions:**
   ```bash
   docker compose down
   docker compose up -d
   ```

### Issue 7: Disk Space Issues

**Symptoms:**
- System running slowly
- "No space left on device" errors

**Solutions:**

1. **Check disk usage:**
   ```bash
   df -h /Users/sethrose/Developer/Github/scanner-feed/
   du -sh /Users/sethrose/Developer/Github/scanner-feed/*
   ```

2. **Clean up old logs:**
   ```bash
   # Delete logs older than 7 days
   find /Users/sethrose/Developer/Github/scanner-feed/logs/ -name "*.csv" -mtime +7 -delete
   
   # Compress old logs
   find /Users/sethrose/Developer/Github/scanner-feed/logs/ -name "*.csv" -mtime +2 -exec gzip {} \;
   ```

3. **Clean up temporary segments:**
   ```bash
   rm -rf /Users/sethrose/Developer/Github/scanner-feed/runtime/segments/*
   ```

4. **Check Docker disk usage:**
   ```bash
   docker system df
   docker system prune -f
   ```

### Issue 8: Network Connectivity Problems

**Symptoms:**
- Can't connect to audio feeds
- "Connection timeout" errors

**Solutions:**

1. **Test network connectivity:**
   ```bash
   ping broadcastify.cdnstream1.com
   ```

2. **Check firewall settings:**
   - Ensure Docker can access external networks
   - Check macOS firewall settings

3. **Test feed URL directly:**
   ```bash
   curl -I "https://broadcastify.cdnstream1.com/31880"
   ```

4. **Check proxy settings:**
   ```bash
   env | grep -i proxy
   ```

### Issue 9: Launchd Service Issues

**Symptoms:**
- Parakeet server won't start via launchd
- Service shows as loaded but not running

**Solutions:**

1. **Check service status:**
   ```bash
   launchctl list | grep scanner-feed
   ```

2. **View service logs:**
   ```bash
   log show --predicate 'subsystem == "com.scanner-feed.parakeet"' --last 1h
   ```

3. **Reload service:**
   ```bash
   launchctl bootout "gui/$(id -u)/com.scanner-feed.parakeet"
   launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.scanner-feed.parakeet.plist
   launchctl kickstart -k "gui/$(id -u)/com.scanner-feed.parakeet"
   ```

4. **Check plist file:**
   ```bash
   cat ~/Library/LaunchAgents/com.scanner-feed.parakeet.plist
   ```

### Issue 10: MLX Model Download Issues

**Symptoms:**
- First startup takes very long
- "Model not found" errors
- High memory usage during startup

**Solutions:**

1. **Check model cache:**
   ```bash
   ls -lh ~/.cache/huggingface/hub/
   ```

2. **Manual model download:**
   ```bash
   # Activate virtual environment
   source .venv/bin/activate
   
   # Download model manually
   python3 -c "from huggingface_hub import snapshot_download; snapshot_download('mlx-community/parakeet-tdt-0.6b-v3')"
   ```

3. **Check available disk space:**
   ```bash
   df -h ~/.cache/huggingface/
   ```

## Diagnostic Commands Reference

### System Status
```bash
# Full system status
./docs/scripts/system-status.sh
```

### Log Analysis
```bash
# Count transcription events
wc -l /Users/sethrose/Developer/Github/scanner-feed/runtime/scanner-feed.txt

# Check for errors in logs
docker compose logs scanner | grep -i error

# Check audio levels
docker compose logs scanner | grep -i rms
```

### Network Diagnostics
```bash
# Test feed connectivity
curl -I "https://broadcastify.cdnstream1.com/31880"

# Check DNS resolution
nslookup broadcastify.cdnstream1.com

# Test local ports
nc -zv 127.0.0.1 18765
nc -zv 127.0.0.1 49173
```

### Resource Monitoring
```bash
# Docker resource usage
docker stats scanner-feed-worker

# Disk usage
du -sh /Users/sethrose/Developer/Github/scanner-feed/*

# Memory usage
top -l 1 | grep "PhysMem"
```

## Getting More Help

### Check System Logs
```bash
# System logs for launchd
log show --last 1h --predicate 'subsystem == "com.scanner-feed.parakeet"'

# Docker daemon logs
log show --last 1h --predicate 'subsystem == "com.docker.docker"'
```

### Community Support
- Check the project's GitHub issues
- Review the README.md for additional information

### Debug Mode
To enable more verbose logging, edit `docker-compose.yml` and add:
```yaml
environment:
  - LOG_LEVEL=DEBUG
```

Then restart the container:
```bash
docker compose down
docker compose up -d
```

## Common Error Messages

### "Connection refused"
- Parakeet server not running
- Check server status and restart

### "No such file or directory"
- Missing configuration file
- Check file paths in docker-compose.yml

### "Permission denied"
- File permission issues
- Check directory permissions

### "Out of memory"
- Insufficient RAM
- Close other applications or increase Docker memory allocation

### "Model not found"
- MLX model download failed
- Check network connectivity and disk space

## Next Steps

If you're still having issues after trying these solutions:

1. **Collect diagnostic information:**
   ```bash
   # Run diagnostic script
   ./docs/scripts/diagnostics.sh > ~/scanner-diagnostics-$(date +%Y%m%d).txt
   ```

2. **Check the logs:**
   ```bash
   docker compose logs --tail 100 scanner > ~/scanner-logs-$(date +%Y%m%d).txt
   ```

3. **Review the architecture:**
   See [Architecture](./architecture.md) to understand how the system works

4. **Contact support:**
   - Include diagnostic output
   - Describe what you were trying to do
   - List what you've already tried
