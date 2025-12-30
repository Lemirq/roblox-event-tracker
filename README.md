# Park a Car Event Tracker

Wanted to overengineer and track when special events happened in the Roblox game called "Park a Car" so I built this system that monitors the game via OBS or native window capture and alerts when specific words appear on screen using OCR. Also includes some anti-idle utilities for staying active in Roblox.

## Features

- **Native Window Monitor** (`native.py`) - Captures any window directly using macOS Quartz APIs (no OBS needed). Uses Vision framework for OCR with configurable crop regions and downscaling for performance.
- **OBS Event Monitor** (`obs.py`) - Captures your OBS scene in real-time and uses macOS Vision framework to detect text. Alerts when target words appear on screen. Includes built-in performance monitoring (FPS, processing times).
- **Autoclicker** (`main.py`) - Toggleable auto-clicker with Alt+X
- **Anti-Idle Script** (`roblox-inactivity.py`) - Performs random realistic actions (walk, jump, camera rotate) to prevent disconnects
- **Quick Toggle** (`autoclick_toggle.scpt`) - AppleScript for quick autoclicker on/off
- **Raycast Integration** - Toggle autoclicker via Raycast hotkey

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

### Native Window Monitor (Recommended)

```bash
python native.py
```

This will:
- Display an interactive window selector (use arrow keys to navigate, Enter to select)
- Capture the selected window directly (no OBS needed)
- Crop to a configurable region (default: middle third horizontally, top half vertically)
- Downscale the image for faster processing (default: 50%)
- Perform OCR using macOS Vision framework
- Print detected text and play sound when target words appear
- Show a preview window of what's being captured
- Display performance stats every 5 seconds

**Configuration** (edit `native.py`):
```python
TARGET_WORDS = ["Exclusive", "Hacker"]  # Words to detect

# Crop settings (0.0 to 1.0)
CROP_H_START = 1/3                 # Horizontal start (left edge)
CROP_H_END = 2/3                   # Horizontal end (right edge)
CROP_V_START = 1/8                 # Vertical start (top edge)
CROP_V_END = 0.5                   # Vertical end (bottom edge)

# Performance settings
FAST_MODE = False                  # True for faster but less accurate OCR
SCALE_FACTOR = 0.5                 # Downscale factor (0.5 = half size, faster)
COOLDOWN = 2.0                     # Seconds between alerts
```

Press `Ctrl+C` to stop.

### Event Monitor (OBS)

```bash
python obs.py
```

This will:
- Connect to OBS WebSocket
- Capture the specified scene at 320x180 resolution
- Perform OCR using macOS Vision framework
- Print detected text and play sound when target words appear
- Show a preview window of what's being captured
- Display performance stats every 5 seconds (FPS, processing times)

**Performance Stats Displayed:**
- FPS: Frames per second over last 30 frames
- Capture time: Time to fetch screenshot from OBS (ms)
- Convert time: Time to convert to CGImage format (ms)
- OCR time: Time for Vision framework to process (ms)
- Total: Combined processing time (ms)

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

### Raycast Integration

Create a Raycast Script to toggle the cliclick-based autoclicker:

1. Open Raycast Settings → Extensions → Scripts
2. Create a new Script with:
   - **Name**: Autoclicker
   - **Type**: AppleScript
   - **Source**:
     ```applescript
     #!/usr/bin/osascript

     # Required parameters:
     # @raycast.schemaVersion 1
     # @raycast.title Autoclicker
     # @raycast.mode silent

     # Optional parameters:
     # @raycast.icon 🤖

     # Documentation:
     # @raycast.author Vihaan
     # @raycast.authorURL https://vhaan.me

     set flagFile to "/tmp/autoclicker_running"

     if (do shell script "test -f " & flagFile & " && echo yes || echo no") is "no" then
         do shell script "touch " & flagFile
         do shell script "nohup sh -c 'while [ -f " & flagFile & " ]; do cliclick c:. ; sleep 0.01; done' >/dev/null 2>&1 &"
     else
         do shell script "rm " & flagFile
     end if
     ```
3. Assign a hotkey in Raycast (e.g., `Option+X`)

## Configuration

### native.py Settings

```python
# Window is selected interactively at launch
CROP_H_START = 1/3         # Crop horizontal start (0-1)
CROP_H_END = 2/3           # Crop horizontal end (0-1)
CROP_V_START = 1/8         # Crop vertical start (0-1)
CROP_V_END = 0.5           # Crop vertical end (0-1)
SCALE_FACTOR = 0.5         # Downscale factor (lower = faster, less accurate)
FAST_MODE = False          # Fast OCR mode (less accurate)
COOLDOWN = 2.0             # Seconds between alerts
```

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

### virtual_camera_monitor.py Settings

```python
CAMERA_INDEX = 2           # Camera device index (try 0, 1, 2)
CAPTURE_WIDTH = 640        # Capture resolution (lower = faster)
CAPTURE_HEIGHT = 480
FAST_MODE = False           # Fast OCR (set False for accurate mode)
INTERVAL = 0.5             # Capture interval in seconds
```

## How It Works

### Native Window Monitor

1. Displays interactive window picker at launch
2. Captures selected window using Quartz CGWindowListCreateImage
3. Crops to specified region to focus on relevant area
4. Downscales image for faster OCR processing
5. Uses macOS Vision framework's VNRecognizeTextRequest for OCR
6. Searches detected text for target words
7. Plays system sound and prints alert when match found

### OBS Event Monitor

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

**"No windows found matching..."** (native.py)
- Make sure windows are visible on screen
- Press 'q' to quit the window selector if needed

**"Failed to connect to OBS"**
- Make sure OBS is running
- Check WebSocket is enabled in OBS Settings
- Verify password and port (default: 4455)

**No text detected**
- For native.py: Adjust crop region to focus on text area, try SCALE_FACTOR = 1.0
- For obs.py: Check that the source/scene names match exactly in OBS
- Try switching FAST_MODE to see if accuracy improves
- Ensure text is readable in the captured preview window

**Autoclicker not working**
- Give accessibility permissions to your terminal/script editor
- Check that the window is active when clicking
