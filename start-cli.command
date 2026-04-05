#!/bin/bash
# ================================================================
# PORTABLE AI - CLI MODE (Mac)
# ================================================================

cd "$(dirname "$0")"
USB_DIR=$(pwd)
VENV="$USB_DIR/cli-anything/venv"
BIN="$VENV/bin"
export OLLAMA_MODELS="$USB_DIR/ollama/data"

# Check CLI installed
if [ ! -f "$BIN/cli-anything-ollama" ]; then
    echo ""
    echo " CLI-Anything ยังไม่ได้ติดตั้ง"
    echo " กรุณารัน: bash install-cli.sh"
    echo ""
    read -p "กด Enter ออก..."
    exit 1
fi

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo " กำลังเริ่ม Ollama engine..."
    OLLAMA_BIN=""
    if [ -f "$USB_DIR/ollama_mac/Ollama.app/Contents/MacOS/Ollama" ]; then
        OLLAMA_BIN="$USB_DIR/ollama_mac/Ollama.app/Contents/MacOS/Ollama"
    elif [ -f "$USB_DIR/ollama_mac/ollama" ]; then
        OLLAMA_BIN="$USB_DIR/ollama_mac/ollama"
    fi
    if [ -n "$OLLAMA_BIN" ]; then
        "$OLLAMA_BIN" serve > /dev/null 2>&1 &
        sleep 3
    fi
fi

show_menu() {
    clear
    echo ""
    echo "  ██████╗  ██████╗ ██████╗ ████████╗ █████╗ ██████╗ ██╗     ███████╗"
    echo "  ██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝"
    echo "  ██████╔╝██║   ██║██████╔╝   ██║   ███████║██████╔╝██║     █████╗  "
    echo "  ██╔═══╝ ██║   ██║██╔══██╗   ██║   ██╔══██║██╔══██╗██║     ██╔══╝  "
    echo "  ██║     ╚██████╔╝██║  ██║   ██║   ██║  ██║██████╔╝███████╗███████╗"
    echo "  ╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝"
    echo ""
    echo "  Portable AI - CLI-Anything Mode"
    echo "  ═══════════════════════════════════════════"
    echo ""
    echo "  [1] ollama      — จัดการ model และ chat"
    echo "  [2] browser     — ควบคุม browser อัตโนมัติ"
    echo "  [3] libreoffice — สร้างและแก้ไขเอกสาร"
    echo "  [4] UI (chat)   — เปิด chat.html ใน browser"
    echo "  [Q] ออก"
    echo ""
    read -p "  เลือก (1/2/3/4/Q): " CHOICE

    case "$CHOICE" in
        1)
            echo ""
            echo "  ── Ollama REPL ─────────────────────────────────────────────"
            echo "  พิมพ์ help เพื่อดูคำสั่ง, Ctrl+C เพื่อออก"
            echo "  ────────────────────────────────────────────────────────────"
            echo ""
            source "$BIN/activate"
            cli-anything-ollama
            echo ""
            read -p "  กด Enter เพื่อกลับเมนู..."
            show_menu
            ;;
        2)
            echo ""
            echo "  ── Browser Automation REPL ──────────────────────────────────"
            echo "  ต้องการ DOMShell: npx @apireno/domshell + Chrome extension"
            echo "  ────────────────────────────────────────────────────────────"
            echo ""
            source "$BIN/activate"
            cli-anything-browser
            echo ""
            read -p "  กด Enter เพื่อกลับเมนู..."
            show_menu
            ;;
        3)
            echo ""
            echo "  ── LibreOffice REPL ──────────────────────────────────────────"
            echo "  ต้องการ LibreOffice ติดตั้งในเครื่อง"
            echo "  ────────────────────────────────────────────────────────────"
            echo ""
            source "$BIN/activate"
            cli-anything-libreoffice
            echo ""
            read -p "  กด Enter เพื่อกลับเมนู..."
            show_menu
            ;;
        4)
            open "$USB_DIR/chat.html"
            show_menu
            ;;
        q|Q)
            echo "  ออกจาก CLI Mode"
            exit 0
            ;;
        *)
            show_menu
            ;;
    esac
}

show_menu
