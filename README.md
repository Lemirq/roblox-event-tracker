# Park a Car Event Tracker

Wanted to overengineer and track when special events happened in the Roblox game called "Park a Car" so I built this system that monitors the game via OBS and alerts when specific words appear on screen using OCR. Also includes some anti-idle utilities for staying active in Roblox.

## Features

- **OBS Event Monitor** (`obs.py`) - Captures your OBS scene in real-time and uses macOS Vision framework to detect text. Alerts when target words appear on screen.
- **Autoclicker** (`main.py`) - Toggleable auto-clicker with Alt+X
- **Anti-Idle Script** (`roblox-inactivity.py`) - Performs random realistic actions (walk, jump, camera rotate) to prevent disconnects
- **Quick Toggle** (`autoclick_toggle.scpt`) - AppleScript for quick autoclicker on/off

## Requirements

- macOS (required for Vision framework)
- OBS Studio running with websocket enabled
- Python 3.13+

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

Or using uv:

```bash
uv sync
```

### 2. Configure OBS

1. Install [obs-websocket-js](https://github.com/obsproject/obs-websocket) in OBS
2. Enable WebSocket in OBS Settings → WebSocket
3. Set your password in `obs.py`

### 3. Configure the Event Monitor

Edit `obs.py` and update these settings:

```python
OBS_SOURCE_NAME = "Window Capture"  # Your OBS source name
OBS_SCENE_NAME = "Roblox"            # Your OBS scene name
OBS_PASSWORD = "your_password"       # OBS WebSocket password
TARGET_WORDS = ["Exclusive", "Secret", "Hacker"]  # Words to detect
```

## Usage

### Event Monitor

```bash
python obs.py
```

This will:
- Connect to OBS WebSocket
- Capture the specified scene at 320x180 resolution
- Perform OCR using macOS Vision framework
- Print detected text and play sound when target words appear
- Show a preview window of what's being captured

Press `Ctrl+C` to stop.

### Autoclicker

```bash
python main.py
```

Press `Alt+X` to toggle clicking on/off.

### Anti-Idle Script

```bash
python roblox-inactivity.py
```

Switch to your Roblox window within 5 seconds. The script will randomly walk, jump, and rotate the camera every 2-4 minutes to prevent AFK disconnects.

Move mouse to top-left corner or press `Ctrl+C` to stop.

### Quick Toggle (AppleScript)

Double-click `autoclick_toggle.scpt` to toggle the cliclick-based autoclicker.

## Configuration

### obs.py Settings

```python
CAPTURE_WIDTH = 320        # Width of captured image (lower = faster)
CAPTURE_HEIGHT = 180       # Height of captured image (lower = faster)
FAST_MODE = True           # Fast OCR (set False for accurate mode)
COOLDOWN = 2.0             # Minimum seconds between alerts
INTERVAL = 0.5             # Capture interval in seconds
```

### main.py Settings

```python
CLICK_DELAY = 0.01         # Seconds between clicks
```

### roblox-inactivity.py Settings

```python
wait_time = random.randint(120, 240)  # Action interval (2-4 minutes)
```

## How It Works

### Event Monitor

1. Connects to OBS WebSocket
2. Captures screenshots of the specified scene
3. Converts images to CGImage format
4. Uses macOS Vision framework's VNRecognizeTextRequest for OCR
5. Searches detected text for target words
6. Plays system sound and prints alert when match found

### Anti-Idle

- Performs random human-like movements at random intervals
- Smooth mouse movement curves instead of instant teleports
- 30% chance to do double actions (e.g., walk AND jump)

## Troubleshooting

**"Failed to connect to OBS"**
- Make sure OBS is running
- Check WebSocket is enabled in OBS Settings
- Verify password and port (default: 4455)

**No text detected**
- Check that the source/scene names match exactly in OBS
- Try lowering the resolution or switching to FAST_MODE
- Ensure text is readable in the captured preview window

**Autoclicker not working**
- Give accessibility permissions to your terminal/script editor
- Check that the window is active when clicking
