# Voice Recognition Examples

## Example 1: Basic Transcription

**Input**: User sends voice message "你好,今天天气怎么样?"

**Command**:
```bash
whisper /home/admin/.openclaw/media/inbound/audio.ogg \
  --language Chinese \
  --model tiny \
  --output_format txt
```

**Output**:
```
[00:00.000 --> 00:03.000] 你好,今天天气怎么样?
```

**Agent response**:
```
📝 You said: "你好,今天天气怎么样?"

北京今天多云,气温 5-12°C...
```

---

## Example 2: Technical Content

**Input**: Voice message "帮我解释一下 Transformer 的 self-attention 机制"

**Transcription** (tiny model may struggle):
```
[00:00.000 --> 00:08.000] 帮我解释一下 transfer 的 self attention 机制
```

**Note**: Technical terms may be transcribed incorrectly. Agent should:
1. Show transcription with 📝 prefix
2. Ask for clarification if term seems wrong
3. Suggest user type technical terms for accuracy

---

## Example 3: First-Time Installation

**Scenario**: New user sends voice, Whisper not installed

**Agent workflow**:

```python
# 1. Detect voice attachment
if audio_file_detected:
    # 2. Check if whisper exists
    result = exec("which whisper")
    
    if result.error or "no whisper" in result.output:
        # 3. Inform user
        reply("🔧 Setting up voice recognition (first time, ~2 minutes)...")
        
        # 4. Run installation
        exec("/home/admin/.openclaw/workspace/skills/voice-recognition/install.sh")
        
        # 5. Confirm
        reply("✅ Voice recognition ready! Transcribing your message...")
    
    # 6. Transcribe
    transcription = exec("whisper audio.ogg --language Chinese --model tiny ...")
    
    # 7. Process
    reply(f"📝 You said: \"{transcription}\"")
    process_user_message(transcription)
```

---

## Example 4: Out of Memory Error

**Command**:
```bash
whisper audio.ogg --language Chinese --model base
```

**Error**:
```
Command aborted by signal SIGKILL
```

**Agent recovery**:

```python
try:
    # Try base model first
    result = exec("whisper audio.ogg --model base ...")
except:
    # Fallback to tiny
    reply("⚠️ Using lightweight model for transcription...")
    result = exec("whisper audio.ogg --model tiny ...")
```

---

## Example 5: Mixed Language

**Input**: Voice with Chinese + English

**Command** (auto-detect):
```bash
whisper audio.ogg --model tiny --output_format txt
```

**Or specify primary language**:
```bash
whisper audio.ogg --language Chinese --model tiny
```

**Transcription**:
```
[00:00.000 --> 00:05.000] 我想了解一下 GPT-4 的 training details
```

---

## Example 6: Long Audio (60+ seconds)

**Strategy**: Warn user if duration > 30 seconds

```python
if audio_duration > 30:
    reply("⏳ Processing long audio (~60 sec), this may take a moment...")
    
# Use tiny model for speed
result = exec("whisper audio.ogg --language Chinese --model tiny")
```

**Expected time**: ~10-15 seconds for 60-second audio

---

## Example 7: Unclear Audio / Background Noise

**Transcription result**:
```
[00:00.000 --> 00:03.000] 你好 [NOISE] 今天 [UNCLEAR] 怎么样
```

**Agent response**:
```
📝 I heard: "你好 [NOISE] 今天 [UNCLEAR] 怎么样"

Sorry, parts of your voice message were unclear due to background noise.
Could you please:
1. Repeat in a quieter environment, or
2. Type your message for clarity
```

---

## Example 8: Format Conversion

**Input**: Unsupported format (`.amr`)

**Workflow**:
```bash
# 1. Detect unsupported format
file audio.amr
# Output: AMR audio

# 2. Convert to supported format
ffmpeg -i audio.amr -ar 16000 -ac 1 audio.wav

# 3. Transcribe
whisper audio.wav --language Chinese --model tiny
```

---

## Example 9: Batch Processing

**Scenario**: User sends multiple voice messages quickly

**Strategy**:
```python
for audio_file in audio_queue:
    transcription = transcribe(audio_file)
    accumulated_text += transcription + " "

reply(f"📝 Your messages: \"{accumulated_text}\"")
process_user_message(accumulated_text)
```

---

## Example 10: Quality Comparison

**Same audio, different models**:

| Model | Transcription | Accuracy | Time |
|-------|--------------|----------|------|
| tiny  | "你好,今天天气怎么样" | 95% | 1.2s |
| base  | "你好,今天天气怎么样?" | 98% | 2.5s |
| small | "你好,今天的天气怎么样?" | 99% | 8.0s |

**Recommendation**: Default to `tiny`, offer `base` for critical transcriptions

---

## Common Pitfall Solutions

### Pitfall 1: No output file
**Cause**: Output dir doesn't exist

**Solution**:
```bash
mkdir -p /tmp/whisper_output
whisper audio.ogg --output_dir /tmp/whisper_output
```

### Pitfall 2: Encoding issues
**Cause**: Special characters in file path

**Solution**:
```bash
# Use full absolute path
whisper "/home/admin/.openclaw/media/inbound/audio file (1).ogg"
```

### Pitfall 3: Model not cached
**Symptom**: Downloading model every time

**Check cache**:
```bash
ls ~/.cache/whisper/
```

**Expected**: `tiny.pt`, `base.pt` after first run

---

## Performance Benchmarks

**Test system**: Alibaba Cloud ECS (2 vCPU, 4GB RAM)

| Audio Length | Model | Time | Memory |
|--------------|-------|------|--------|
| 3s           | tiny  | 1.2s | 450MB  |
| 5s           | tiny  | 1.8s | 480MB  |
| 10s          | tiny  | 2.5s | 500MB  |
| 30s          | tiny  | 6.0s | 550MB  |
| 3s           | base  | KILLED | >2GB |

**Conclusion**: Use `tiny` on systems with <4GB RAM
