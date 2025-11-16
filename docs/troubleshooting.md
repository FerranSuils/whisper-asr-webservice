# Troubleshooting

## Network and Model Download Issues

### Problem: DNS Resolution Failure

If you encounter an error like:
```
urllib.error.URLError: <urlopen error [Errno -3] Temporary failure in name resolution>
```

This means the container cannot download the Whisper model due to DNS resolution issues.

#### Solutions:

##### 1. Use Google DNS (Recommended)

Add DNS servers to your docker-compose.yml:

```yaml
services:
  whisper-asr-webservice:
    dns:
      - 8.8.8.8
      - 8.8.4.4
```

Or use the command line:

```bash
docker run --dns 8.8.8.8 --dns 8.8.4.4 -p 9000:9000 \
  -e ASR_MODEL=base \
  onerahmet/openai-whisper-asr-webservice:latest
```

##### 2. Pre-download Models with Cache Volume

Create a cache directory and download models before starting:

```bash
# Create cache directory
mkdir -p cache

# Run with cache volume
docker run -d -p 9000:9000 \
  -v $PWD/cache:/root/.cache \
  -e ASR_MODEL=base \
  onerahmet/openai-whisper-asr-webservice:latest
```

On first run, ensure your host has internet access. The models will be downloaded to the cache directory and reused on subsequent runs.

##### 3. Manual Model Download

Download the model manually and mount it:

```bash
# Download model using Python on your host machine
python3 -c "
import whisper
whisper.load_model('base', download_root='./models')
"

# Run container with model directory
docker run -d -p 9000:9000 \
  -v $PWD/models:/root/.cache/whisper \
  -e ASR_MODEL=base \
  onerahmet/openai-whisper-asr-webservice:latest
```

##### 4. Configure Docker Daemon DNS

Edit `/etc/docker/daemon.json` on Linux or Docker Desktop settings on Windows/Mac:

```json
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}
```

Then restart Docker:

```bash
# Linux
sudo systemctl restart docker

# Windows/Mac: Restart Docker Desktop
```

## Large File Upload Issues

### Problem: File Upload Fails for Large Audio Files

If uploads fail for large files, ensure:

1. **Check MAX_FILE_SIZE configuration:**
   ```bash
   export MAX_FILE_SIZE=0  # 0 = unlimited
   ```

2. **Increase timeout settings** in your reverse proxy (nginx, apache, etc.)

3. **Monitor server resources:**
   - Ensure sufficient RAM for large files
   - Check disk space in /tmp directory

### Problem: Container Runs Out of Memory

For large files, increase Docker memory limits:

```bash
docker run -d -p 9000:9000 \
  --memory="4g" \
  --memory-swap="8g" \
  onerahmet/openai-whisper-asr-webservice:latest
```

Or in docker-compose.yml:

```yaml
services:
  whisper-asr-webservice:
    deploy:
      resources:
        limits:
          memory: 4G
```

## Model Loading Issues

### Problem: Model Takes Too Long to Load

Use the cache volume to persist models:

```bash
docker run -d -p 9000:9000 \
  -v whisper-cache:/root/.cache \
  onerahmet/openai-whisper-asr-webservice:latest
```

### Problem: Out of Memory When Loading Large Models

For models like `large-v3`, ensure sufficient memory:

- **CPU**: At least 8GB RAM
- **GPU**: At least 6GB VRAM for large models

Consider using smaller models (`base`, `small`) or quantization:

```bash
export ASR_MODEL=base
export ASR_QUANTIZATION=int8  # For CPU
```

## GPU Issues

### Problem: CUDA Out of Memory

Reduce batch size or use a smaller model:

```bash
export ASR_MODEL=medium
export ASR_QUANTIZATION=float16
```

### Problem: GPU Not Detected

Verify NVIDIA Docker runtime:

```bash
# Check GPU is visible
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Use correct docker-compose file
docker-compose -f docker-compose.gpu.yml up
```

## Permission Issues

### Problem: Cannot Write to Cache Directory

Ensure proper permissions on mounted volumes:

```bash
# Linux/Mac
chmod 777 cache/

# Or run with proper user
docker run -u $(id -u):$(id -g) ...
```

## API Issues

### Problem: Transcription Takes Too Long

Check:

1. **Model size**: Smaller models are faster
2. **Audio length**: Long audio takes longer
3. **VAD filter**: Enable to skip silence
4. **Device**: GPU is much faster than CPU

### Problem: Language Detection Issues

Specify language explicitly for better accuracy:

```bash
curl -X POST http://localhost:9000/asr \
  -F "audio_file=@audio.mp3" \
  -F "language=es"
```

## Getting Help

If problems persist:

1. Check logs: `docker logs <container-id>`
2. Verify environment variables: `docker exec <container-id> env`
3. Test network: `docker exec <container-id> ping google.com`
4. Join our Discord: [https://discord.gg/4Q5YVrePzZ](https://discord.gg/4Q5YVrePzZ)
5. Open an issue: [GitHub Issues](https://github.com/ahmetoner/whisper-asr-webservice/issues)
