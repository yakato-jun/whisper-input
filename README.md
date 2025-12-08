# Whisper Input

A desktop voice input tool that uses OpenAI Whisper API for speech-to-text transcription.

Press a trigger key (default: Right Ctrl) to record your voice, and the transcribed text is automatically inserted at your cursor position.

## Features

- **Hold mode**: Record while holding the trigger key
- **Toggle mode**: Press to start, press again to stop
- **Cross-platform**: Linux (X11) and Windows 10/11
- **Auto-paste**: Optionally paste transcribed text automatically

## Requirements

- Python 3.10+
- OpenAI API key
- Linux: xdotool, xclip, portaudio19-dev
- Windows: No additional system dependencies

## Installation

### Linux

```bash
git clone https://github.com/yakato-jun/whisper-input.git
cd whisper-input
./setup.sh
```

### Windows

```cmd
git clone https://github.com/yakato-jun/whisper-input.git
cd whisper-input
setup.bat
```

## Usage

```bash
# Set your API key
export OPENAI_API_KEY="your-api-key"  # Linux
set OPENAI_API_KEY=your-api-key       # Windows

# Activate virtual environment
source .venv/bin/activate  # Linux
.venv\Scripts\activate     # Windows

# Run
python main.py
```

## Configuration

Settings can be configured via environment variables or `config.json`:

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| API Key | `OPENAI_API_KEY` | (required) | OpenAI API key |
| Trigger Key | `VOICE_INPUT_TRIGGER` | `ctrl_r` | Key to start/stop recording |
| Mode | `VOICE_INPUT_MODE` | `hold` | `hold` or `toggle` |
| Auto Paste | `VOICE_INPUT_AUTO_PASTE` | `false` | Auto-paste transcribed text |
| Model | `VOICE_INPUT_MODEL` | `whisper-1` | Whisper model to use |

### config.json example

```json
{
  "trigger_key": "ctrl_r",
  "mode": "hold",
  "auto_paste": true
}
```

### Available trigger keys

`ctrl_r`, `ctrl_l`, `alt_r`, `alt_gr`, `f12`, and other `pynput.keyboard.Key` names.

## License

MIT
