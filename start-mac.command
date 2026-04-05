#!/bin/bash
# ================================================================
# PORTABLE AI - MAC LAUNCHER
# Gemma 4 E2B + E4B Dual-Model Edition
# ================================================================

cd "$(dirname "$0")"
USB_DIR=$(pwd)
MAC_OLLAMA_DIR="$USB_DIR/ollama_mac"
DATA_DIR="$USB_DIR/ollama/data"
CONFIG="$USB_DIR/active-model.txt"

echo "==================================================="
echo "    Portable AI - Gemma 4 E2B + E4B Edition"
echo "==================================================="
echo ""

# Read active model from config
if [ -f "$CONFIG" ]; then
    ACTIVE_MODEL=$(cat "$CONFIG")
else
    ACTIVE_MODEL="gemma4:e4b"
fi

# Model selection menu
echo "  Current model: $ACTIVE_MODEL"
echo ""
echo "  [1] gemma4:e2b  - Fast, works on any machine (~1.5 GB RAM)"
echo "  [2] gemma4:e4b  - Better quality, needs 8 GB RAM"
echo "  [3] Keep current ($ACTIVE_MODEL)"
echo ""
read -p "  Select model (1/2/3, or Enter to keep current): " CHOICE

case "$CHOICE" in
    1)
        ACTIVE_MODEL="gemma4:e2b"
        echo "$ACTIVE_MODEL" > "$CONFIG"
        echo "  Switched to gemma4:e2b"
        ;;
    2)
        ACTIVE_MODEL="gemma4:e4b"
        echo "$ACTIVE_MODEL" > "$CONFIG"
        echo "  Switched to gemma4:e4b"
        ;;
esac

echo ""
echo "  Starting with: $ACTIVE_MODEL"
echo ""

# -----------------------------------------------------------------
# Download Mac Ollama Engine (first time only)
# -----------------------------------------------------------------
if [ ! -d "$MAC_OLLAMA_DIR/Ollama.app" ] && [ ! -f "$MAC_OLLAMA_DIR/ollama" ]; then
    echo "First time on Mac! Downloading the AI Engine..."
    mkdir -p "$MAC_OLLAMA_DIR"
    curl -L --progress-bar "https://github.com/ollama/ollama/releases/latest/download/ollama-darwin.zip" -o "$MAC_OLLAMA_DIR/ollama-darwin.zip"
    echo "Extracting..."
    unzip -o -q "$MAC_OLLAMA_DIR/ollama-darwin.zip" -d "$MAC_OLLAMA_DIR/"
    rm "$MAC_OLLAMA_DIR/ollama-darwin.zip"
    if [ -f "$MAC_OLLAMA_DIR/Ollama.app/Contents/MacOS/Ollama" ]; then
        chmod +x "$MAC_OLLAMA_DIR/Ollama.app/Contents/MacOS/Ollama"
    elif [ -f "$MAC_OLLAMA_DIR/ollama" ]; then
        chmod +x "$MAC_OLLAMA_DIR/ollama"
    fi
    echo "Mac Engine Setup Complete!"
    echo ""
fi

# -----------------------------------------------------------------
# Download AnythingLLM (first time only)
# -----------------------------------------------------------------
if [ ! -d "$USB_DIR/anythingllm_mac/AnythingLLM.app" ]; then
    echo "First time setup: Downloading AnythingLLM directly to USB..."
    mkdir -p "$USB_DIR/anythingllm_mac"
    curl -L --progress-bar "https://cdn.anythingllm.com/latest/AnythingLLMDesktop-Silicon.dmg" -o "$USB_DIR/anythingllm_mac/AnythingLLM_Installer.dmg"
    echo "Extracting AnythingLLM to USB (please wait)..."
    MOUNT_DIR=$(hdiutil attach -nobrowse "$USB_DIR/anythingllm_mac/AnythingLLM_Installer.dmg" | grep -o '/Volumes/.*')
    cp -R "$MOUNT_DIR/AnythingLLM.app" "$USB_DIR/anythingllm_mac/"
    hdiutil detach "$MOUNT_DIR"
    rm "$USB_DIR/anythingllm_mac/AnythingLLM_Installer.dmg"
    xattr -rc "$USB_DIR/anythingllm_mac/AnythingLLM.app"
    echo "AnythingLLM extracted and ready!"
fi

# -----------------------------------------------------------------
# Launch Ollama Engine
# -----------------------------------------------------------------
echo "Starting AI Engine from USB..."

export OLLAMA_MODELS="$DATA_DIR"
export STORAGE_DIR="$USB_DIR/anythingllm_data"
mkdir -p "$STORAGE_DIR"
mkdir -p "$DATA_DIR"

# Find Ollama binary
OLLAMA_BIN=""
if [ -f "$MAC_OLLAMA_DIR/Ollama.app/Contents/MacOS/Ollama" ]; then
    OLLAMA_BIN="$MAC_OLLAMA_DIR/Ollama.app/Contents/MacOS/Ollama"
elif [ -f "$MAC_OLLAMA_DIR/ollama" ]; then
    OLLAMA_BIN="$MAC_OLLAMA_DIR/ollama"
else
    echo "Error: Could not find the Ollama binary on the USB drive!"
    read -p "Press Enter to exit..."
    exit 1
fi

"$OLLAMA_BIN" serve > /dev/null 2>&1 &
OLLAMA_PID=$!
sleep 3

# Pull model if not already on USB
MODEL_EXISTS=$("$OLLAMA_BIN" list 2>/dev/null | grep "$ACTIVE_MODEL")
if [ -z "$MODEL_EXISTS" ]; then
    echo "  Downloading $ACTIVE_MODEL (first time only)..."
    "$OLLAMA_BIN" pull "$ACTIVE_MODEL"
fi

echo ""
echo "==================================================="
echo "  SYSTEM ONLINE: $ACTIVE_MODEL running from USB!"
echo "==================================================="
echo ""

# Launch AnythingLLM
echo "Opening AnythingLLM..."
open --env STORAGE_DIR="$STORAGE_DIR" "$USB_DIR/anythingllm_mac/AnythingLLM.app"

echo ""
echo "  To switch model: quit and restart, pick a different option"
echo "  Keep this terminal open while you chat!"
echo ""
read -p "  Hit [ENTER] to shut down the AI safely..."

kill $OLLAMA_PID 2>/dev/null
killall AnythingLLM 2>/dev/null
echo "AI shut down. You may safely eject the USB."
