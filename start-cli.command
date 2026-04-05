#!/bin/bash
# ================================================================
# PORTABLE AI - CLI-Anything REPL Launcher (Mac)
# ================================================================

cd "$(dirname "$0")"
USB_DIR=$(pwd)
VENV="$USB_DIR/cli-anything/venv"
BIN="$VENV/bin"
export OLLAMA_MODELS="$USB_DIR/ollama/data"

if [ ! -f "$BIN/cli-anything-ollama" ]; then
    echo ""; echo " CLI ยังไม่ได้ติดตั้ง — รัน: bash install-cli.sh ก่อน"; echo ""
    read -p "กด Enter ออก..."; exit 1
fi

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    for bin in "$USB_DIR/ollama_mac/Ollama.app/Contents/MacOS/Ollama" "$USB_DIR/ollama_mac/ollama"; do
        [ -f "$bin" ] && { "$bin" serve > /dev/null 2>&1 & sleep 3; break; }
    done
fi

show_menu() {
    clear
    echo ""
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║        Portable AI — CLI-Anything Edition            ║"
    echo "  ╠══════════════════════════════════════════════════════╣"
    echo "  ║  🤖 AI & Models                                      ║"
    echo "  ║  [1] ollama        — จัดการ model + chat             ║"
    echo "  ║  [2] anygen        — สร้าง slides, docs ด้วย AI      ║"
    echo "  ╠══════════════════════════════════════════════════════╣"
    echo "  ║  📄 เอกสาร & ความรู้                                  ║"
    echo "  ║  [3] libreoffice   — Writer, Calc, Impress           ║"
    echo "  ║  [4] joplin        — Note-taking + knowledge base    ║"
    echo "  ║  [5] jupyterlab    — Notebook + data analysis        ║"
    echo "  ╠══════════════════════════════════════════════════════╣"
    echo "  ║  📐 Diagram & Visual                                  ║"
    echo "  ║  [6] plantuml      — UML + diagrams จาก text         ║"
    echo "  ╠══════════════════════════════════════════════════════╣"
    echo "  ║  🌐 Web & Dev                                         ║"
    echo "  ║  [7] browser       — Browser automation              ║"
    echo "  ║  [8] gitea         — Git server management           ║"
    echo "  ╠══════════════════════════════════════════════════════╣"
    echo "  ║  🎙️ ประชุม                                             ║"
    echo "  ║  [9] meeting       — บันทึก แปล สรุปประชุม           ║"
    echo "  ╠══════════════════════════════════════════════════════╣"
    echo "  ║  [U] UI            — เปิด chat.html                   ║"
    echo "  ║  [Q] ออก                                              ║"
    echo "  ╚══════════════════════════════════════════════════════╝"
    echo ""
    read -p "  เลือก: " CHOICE

    source "$BIN/activate" 2>/dev/null

    run_cli() {
        local cmd=$1; local note=$2
        echo ""; echo "  ── $cmd ──────────────────────────────────────────"
        echo "  $note"; echo "  Ctrl+C เพื่อออก"; echo ""
        $cmd
        echo ""; read -p "  กด Enter กลับเมนู..."; show_menu
    }

    case "$CHOICE" in
        1) run_cli "cli-anything-ollama" "จัดการ Gemma model + chat" ;;
        2) run_cli "cli-anything-anygen" "สร้าง content ด้วย AI" ;;
        3) run_cli "cli-anything-libreoffice" "Writer / Calc / Impress (ต้องการ LibreOffice)" ;;
        4) run_cli "cli-anything-joplin" "Note-taking (ต้องการ Joplin localhost:41184)" ;;
        5) run_cli "cli-anything-jupyterlab" "Notebook (ต้องการ JupyterLab localhost:8888)" ;;
        6) run_cli "cli-anything-plantuml" "UML diagrams จาก text" ;;
        7) run_cli "cli-anything-browser" "Browser automation (ต้องการ DOMShell + Chrome)" ;;
        8) run_cli "cli-anything-gitea" "Git server (ต้องการ Gitea localhost:3000)" ;;
        9) run_cli "cli-anything-meeting" "บันทึก แปล สรุปประชุม (ต้องการ ffmpeg)" ;;
        u|U) open "$USB_DIR/chat.html"; show_menu ;;
        q|Q) echo "  ออกจาก CLI Mode"; exit 0 ;;
        *) show_menu ;;
    esac
}

show_menu
