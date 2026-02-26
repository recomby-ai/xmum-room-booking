#!/bin/bash
# XMUM Room Booking — One-click install as Claude Code Skill

set -e

SKILL_DIR="$HOME/.claude/skills/xmum-room-booking"

echo "=================================================="
echo " XMUM Room Booking Skill — Installer"
echo "=================================================="

# 1. Install skill files
echo ""
echo "[1/3] Installing skill to $SKILL_DIR ..."
rm -rf "$SKILL_DIR"
mkdir -p "$HOME/.claude/skills"
git clone https://github.com/recomby-ai/xmum-room-booking.git /tmp/xmum-room-booking-install
cp -r /tmp/xmum-room-booking-install/skill "$SKILL_DIR"
rm -rf /tmp/xmum-room-booking-install
echo "✓ Skill installed"

# 2. Install Python dependencies
echo ""
echo "[2/3] Installing Python dependencies ..."
pip3 install -q requests beautifulsoup4 google-generativeai Pillow
echo "✓ Dependencies installed"

# 3. First-time setup
echo ""
echo "[3/3] First-time setup ..."
echo "      You will need your XMUM campus ID, password, and a Gemini API Key."
echo "      Get a free Gemini API Key at: https://aistudio.google.com/apikey"
echo ""
python3 "$SKILL_DIR/scripts/auto_booking.py" --setup

echo ""
echo "=================================================="
echo "✓ Installation complete!"
echo ""
echo "Claude Code will now recognise the skill automatically."
echo "You can also run the script directly:"
echo "  python3 ~/.claude/skills/xmum-room-booking/scripts/auto_booking.py"
echo "=================================================="
