#!/bin/bash
# Voice Recognition Setup Script
# Automatically install OpenAI Whisper if not present

set -e

echo "🎙️ Voice Recognition Setup"
echo "=========================="
echo ""

# Check if whisper is already installed
if command -v whisper &> /dev/null; then
    echo "✅ Whisper is already installed:"
    whisper --version 2>&1 | head -1 || echo "   $(which whisper)"
    exit 0
fi

echo "📦 Whisper not found. Starting installation..."
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ffmpeg not found. Installing..."
    brew install ffmpeg
fi

if ! command -v python3 &> /dev/null; then
    echo "⚠️  python3 not found. Installing..."
    brew install python@3.14
fi

if ! command -v pipx &> /dev/null; then
    echo "⚠️  pipx not found. Installing..."
    brew install pipx
fi

echo "✅ All prerequisites ready"
echo ""

# Install Whisper
echo "📥 Installing OpenAI Whisper..."
pipx install openai-whisper

echo ""
echo "✅ Installation complete!"
echo ""
echo "Testing installation..."
whisper --version 2>&1 | head -1 || which whisper

echo ""
echo "🎉 Voice recognition is ready to use!"
echo ""
echo "Usage:"
echo "  whisper audio.ogg --language Chinese --model tiny"
