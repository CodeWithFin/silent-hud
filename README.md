# SilentHUD

A transparent, focus-preserving overlay that provides silent OCR-to-LLM assistance through global hotkeys. Designed as a security research demonstration of accessibility overlay capabilities.

## Features

- **Ghost Window**: Transparent overlay that stays on top without stealing focus
- **Click-Through**: Mouse events pass through to applications below
- **Taskbar Hidden**: Doesn't appear in Alt-Tab or taskbar
- **Global Hotkeys**: Works even when other applications are focused
- **OCR Capture**: Capture and extract text from screen regions
- **AI Responses**: Get answers displayed directly on the overlay

## Installation

```bash
# Clone and enter directory
cd SilentHUD

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Tesseract OCR (system package)
sudo apt install tesseract-ocr libxcb-cursor0
```

## Usage

```bash
# Linux requires root for global keyboard hooks
sudo ./venv/bin/python main.py
```

## 🎮 Controls

| Hotkey | Action | Description |
| :--- | :--- | :--- |
| **`Ctrl` + `Shift` + `X`** | **Toggle Visibility** | Show or hide the overlay/indicator. |
| **Hold `Right Alt`** | **Spyglass Mode** | Shows a blue viewfinder. Move mouse to aim, release to capture & ask AI. |
| **`Alt` + `Scroll`** | **Scroll Text** | Scroll the AI response text up or down. |
| **`Ctrl` + `Shift` + `S`** | **Instant Capture** | Captures region around cursor immediately (Legacy mode). |
| **`Ctrl` + `Shift` + `Z`** | **Panic Button** | Instantly clears all text and hides the overlay. |

> **Note:** "Right Alt" (or AltGr) is used to avoid conflict with typing capital letters or symbols.

## Configuration

Edit `.env` to set your Groq API key:

```
GROQ_API_KEY=your_api_key_here
```

## Project Structure

```
SilentHUD/
├── main.py              # Application entry point
├── src/
│   ├── overlay.py       # PyQt6 ghost window
│   ├── hotkeys.py       # Global hotkey manager
│   ├── ocr.py           # Screen capture + OCR
│   └── llm.py           # Groq API client
├── .env                 # API keys (gitignored)
└── requirements.txt     # Python dependencies
```

## Technical Notes

- Uses PyQt6 with `WindowTransparentForInput` flag for click-through on Linux
- Uses `keyboard` library for global hotkeys without focus theft
- Tesseract OCR with image preprocessing for better accuracy
- Async processing to keep UI responsive during OCR/LLM calls

## 🛡️ Safe Mode
If the application is run in an environment without low-level input access (like some containers or WSL), it will enter **Safe Mode**. In this mode, global hotkeys are disabled to prevent crashes, allowing you to still use the core logic and GUI for research and debugging.
