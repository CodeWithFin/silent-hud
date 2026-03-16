#!/bin/bash
echo "🚀 Building SilentHUD (Disguised as system-audio-helper)..."

# Ensure venv
source ./venv/bin/activate

# Clean previous builds
rm -rf build dist *.spec

# Build with PyInstaller
# --name: The output binary name (Disguise)
# --onefile: Single executable
# --noconsole: No terminal window
# --add-data: Include src folder
# --hidden-import: Ensure dynamic imports are caught
pyinstaller --name "system-audio-helper" \
            --onefile \
            --noconsole \
            --add-data "src:src" \
            --hidden-import "keyboard" \
            --hidden-import "mouse" \
            --hidden-import "PIL" \
            --hidden-import "pytesseract" \
            --hidden-import "groq" \
            --hidden-import "setproctitle" \
            --hidden-import "sounddevice" \
            --hidden-import "numpy" \
            --hidden-import "scipy" \
            main.py

echo "✅ Build Complete!"
echo "📍 Binary Location: dist/system-audio-helper"
