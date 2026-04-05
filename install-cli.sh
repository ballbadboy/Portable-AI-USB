#!/bin/bash
# ================================================================
# PORTABLE AI - CLI-ANYTHING SETUP (Mac/Linux)
# ติดตั้ง CLI harnesses: ollama, browser, libreoffice
# ================================================================

cd "$(dirname "$0")"
USB_DIR=$(pwd)
CLI_DIR="$USB_DIR/cli-anything"
VENV="$CLI_DIR/venv"

echo ""
echo "=========================================================="
echo "   CLI-Anything Setup for Portable AI USB (Mac/Linux)    "
echo "=========================================================="
echo ""

# Check Python
echo "[1/4] ตรวจสอบ Python..."
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
    echo "      ERROR: ไม่พบ Python 3.10+"
    echo "      Mac: brew install python3"
    exit 1
fi
echo "      พบ: $($PY --version)"

# Create venv on USB
echo ""
echo "[2/4] สร้าง Python venv บน USB..."
if [ -f "$VENV/bin/python" ]; then
    echo "      venv มีอยู่แล้ว ข้าม..."
else
    $PY -m venv "$VENV"
    echo "      สร้าง venv สำเร็จ"
fi

PIP="$VENV/bin/pip"
PYTHON="$VENV/bin/python"
"$PIP" install --quiet --upgrade pip

# Install harnesses
echo ""
echo "[3/4] ติดตั้ง CLI harnesses..."

echo "      ollama CLI..."
"$PIP" install --quiet -e "$CLI_DIR/ollama"
echo "      ✓ ollama CLI"

echo "      browser CLI..."
"$PIP" install --quiet -e "$CLI_DIR/browser"
echo "      ✓ browser CLI"

echo "      libreoffice CLI..."
"$PIP" install --quiet -e "$CLI_DIR/libreoffice"
echo "      ✓ libreoffice CLI"

# Verify
echo ""
echo "[4/4] ตรวจสอบการติดตั้ง..."
OK=0
for cmd in cli-anything-ollama cli-anything-browser cli-anything-libreoffice; do
    if [ -f "$VENV/bin/$cmd" ]; then
        echo "      ✓ $cmd"
        OK=$((OK+1))
    else
        echo "      ✗ $cmd ไม่พบ"
    fi
done

echo ""
echo "=========================================================="
if [ "$OK" -eq 3 ]; then
    echo "   CLI-Anything พร้อมใช้งาน! ($OK/3 CLIs)"
    echo "   รัน ./start-cli.command เพื่อเปิด REPL"
else
    echo "   ติดตั้งบางส่วนไม่สำเร็จ ($OK/3)"
fi
echo "=========================================================="
echo ""
