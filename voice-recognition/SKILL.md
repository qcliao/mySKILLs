# Voice Recognition Skill

## Description
Process voice messages from various platforms (Feishu, Telegram, etc.) using OpenAI Whisper for automatic speech-to-text conversion.

## Trigger Conditions
Activate this skill when:
- User sends voice/audio messages (file extensions: `.ogg`, `.mp3`, `.wav`, `.m4a`, `.opus`)
- Media attachments with `audio/*` MIME types are detected
- User explicitly asks to "transcribe audio" or "process voice"

## Prerequisites Check

### Step 1: Check if Whisper is installed
```bash
which whisper
```

**If not found**, proceed to installation.

### Step 2: Check available tools
```bash
which pipx ffmpeg python3
```

## Installation Workflow

### If Whisper is NOT installed:

1. **Install pipx** (if missing):
```bash
brew install pipx
```

2. **Install OpenAI Whisper**:
```bash
pipx install openai-whisper
```

3. **Verify installation**:
```bash
whisper --help
```

### Expected output:
- Install time: ~2-5 minutes (first time)
- Disk space: ~150MB (includes dependencies)
- First model download: ~72MB (tiny) or ~139MB (base)

## Usage Guidelines

### Basic Transcription Command

**Standard command**:
```bash
whisper /path/to/audio.ogg \
  --language Chinese \
  --model tiny \
  --output_format txt \
  --output_dir /tmp
```

### Model Selection Strategy

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| `tiny` | 72MB | Fast | Good | Short messages, quick replies |
| `base` | 139MB | Medium | Better | Standard use (may cause OOM on low-mem systems) |
| `small` | 461MB | Slow | Best | Critical accuracy needs |

**Default choice**: 
- Try `tiny` first (fastest, lowest memory)
- Upgrade to `base` only if accuracy is critical AND system has >2GB free RAM

### Language Detection

**For Chinese users**:
```bash
--language Chinese
```

**For auto-detection** (slower):
```bash
# Omit --language flag, Whisper will auto-detect
```

**For multilingual**:
```bash
--language en  # or any supported language code
```

### Output Handling

**Get text result**:
```bash
# Whisper outputs to stdout with timestamps
# Extract clean text:
whisper audio.ogg --language Chinese --model tiny --output_format txt 2>&1 | grep -A 10 "\[00:"
```

**Alternative**: Parse generated `.txt` file:
```bash
cat /tmp/audio.txt
```

## Error Handling

### Case 1: Process killed (SIGKILL)
**Symptom**: `Command aborted by signal SIGKILL`

**Cause**: Out of memory (model too large)

**Solution**: 
1. Retry with smaller model (`tiny` instead of `base`)
2. Check system memory: `free -h`
3. Consider cloud processing for large files

### Case 2: Missing dependencies
**Symptom**: `ffmpeg not found` or `python3 not found`

**Solution**:
```bash
brew install ffmpeg python@3.14
```

### Case 3: First run slow
**Symptom**: Long wait on first transcription

**Cause**: Downloading model files

**Response**: 
- Inform user: "Downloading Whisper model (~72MB), this is one-time only"
- Subsequent runs will be instant

### Case 4: Audio format not supported
**Symptom**: `Unsupported audio format`

**Solution**: Convert with ffmpeg:
```bash
ffmpeg -i input.xxx -ar 16000 -ac 1 output.wav
whisper output.wav --language Chinese --model tiny
```

## Integration Flow

### When receiving voice message:

1. **Detect attachment**:
   - Check for audio file in media path
   - Verify file exists and is readable

2. **Check prerequisites**:
   ```bash
   if ! command -v whisper &> /dev/null; then
       echo "Installing Whisper (first time setup)..."
       # Run installation workflow
   fi
   ```

3. **Transcribe**:
   ```bash
   whisper /path/to/audio.ogg \
     --language Chinese \
     --model tiny \
     --output_format txt 2>&1 | grep -oP '\[.*?\] \K.*'
   ```

4. **Process result**:
   - Extract transcribed text
   - Reply to user with transcription
   - Optionally include: "📝 (transcribed from voice)"

5. **Handle user intent**:
   - Treat transcription as text input
   - Process commands/questions normally

## User Experience

### First-time user flow:
```
User: [sends voice]
AI: "Setting up voice recognition (one-time, ~2 min)..."
AI: [installs Whisper]
AI: "Done! Transcribing your message..."
AI: "📝 You said: '你好,这是测试'"
AI: [responds to message content]
```

### Subsequent messages:
```
User: [sends voice]
AI: "📝 You said: '帮我查一下天气'"
AI: [processes weather query]
```

## Performance Notes

- **Transcription time**: ~1-2 seconds per 5-second audio (tiny model)
- **Memory usage**: ~500MB (tiny), ~1GB (base)
- **CPU usage**: High during transcription, idle otherwise
- **Network**: Only needed for initial model download

## Platform-Specific Considerations

### Feishu
- Audio format: OGG Opus
- Location: `/home/admin/.openclaw/media/inbound/*.ogg`
- Metadata: `duration` field in JSON

### Telegram
- Audio format: OGG/MP3
- Voice notes vs audio files (handle both)

### WhatsApp
- Audio format: Opus
- May need format conversion

## Limitations

1. **Accuracy**: 
   - Tiny model may misrecognize similar-sounding words
   - Technical jargon might be incorrect
   - Background noise reduces accuracy

2. **Speed**:
   - Real-time transcription not possible
   - 5-second audio = ~2 seconds processing

3. **Language mixing**:
   - Chinese + English mixing may confuse tiny model
   - Consider `--language en` for English-heavy content

## Future Enhancements

- [ ] Support multiple model choices via user preference
- [ ] Cache transcriptions to avoid re-processing
- [ ] Add confidence scores to transcriptions
- [ ] Support speaker diarization (multiple speakers)
- [ ] Integrate with cloud APIs for higher accuracy (Azure/Google)

## References

- Whisper GitHub: https://github.com/openai/whisper
- Supported languages: https://github.com/openai/whisper#available-models-and-languages
- Model comparison: https://github.com/openai/whisper#available-models-and-languages

---

**Last updated**: 2026-02-24  
**Tested on**: Linux (Alibaba Cloud), Homebrew environment  
**Status**: ✅ Production ready
