import base64
import io
import threading
import time

import objc
import obsws_python as obs
import Quartz
import Vision
from AppKit import NSApp, NSApplication, NSBeep, NSImage, NSImageView, NSSound, NSWindow
from Foundation import NSData, NSMakeRect
from PIL import Image
from PyObjCTools import AppHelper


class SoundPlayer:
    """Thread-safe sound player that prevents overlapping sounds"""

    def __init__(self):
        self.is_playing = False
        self.lock = threading.Lock()

    def play_sound(self, sound_name="Glass"):
        """Play a system sound if not already playing"""
        with self.lock:
            if self.is_playing:
                return
            self.is_playing = True

        try:
            sound = NSSound.soundNamed_(sound_name)
            if sound:
                sound.play()
                while sound.isPlaying():
                    time.sleep(0.1)
            else:
                NSBeep()
        finally:
            with self.lock:
                self.is_playing = False


class PreviewWindow(NSWindow):
    """Window to display the captured image"""

    def initWithSize_(self, size):
        width, height = size
        frame = NSMakeRect(100, 100, width, height)

        self = objc.super(
            PreviewWindow, self
        ).initWithContentRect_styleMask_backing_defer_(frame, 15, 2, False)
        if self is None:
            return None

        self.setTitle_("OBS Capture Preview")
        self.setLevel_(1)

        self.image_view = NSImageView.alloc().initWithFrame_(
            NSMakeRect(0, 0, width, height)
        )
        self.image_view.setImageScaling_(1)
        self.setContentView_(self.image_view)

        return self

    def updateImage_(self, pil_image):
        """Update the displayed image on main thread"""
        img_bytes = io.BytesIO()
        pil_image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        ns_data = NSData.dataWithBytes_length_(img_bytes.read(), img_bytes.tell())
        ns_image = NSImage.alloc().initWithData_(ns_data)

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "setImageOnMainThread:", ns_image, False
        )

    def setImageOnMainThread_(self, ns_image):
        """Actually set the image (called on main thread)"""
        self.image_view.setImage_(ns_image)


def pil_to_cgimage(pil_image):
    """Convert PIL Image to CGImage"""
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")

    width, height = pil_image.size
    data = pil_image.tobytes()

    data_provider = Quartz.CGDataProviderCreateWithData(None, data, len(data), None)

    color_space = Quartz.CGColorSpaceCreateDeviceRGB()

    cg_image = Quartz.CGImageCreate(
        width,
        height,
        8,
        32,
        width * 4,
        color_space,
        Quartz.kCGImageAlphaLast,
        data_provider,
        None,
        False,
        Quartz.kCGRenderingIntentDefault,
    )

    return cg_image


def detect_text_in_image(cg_image, fast_mode=False):
    """Use Vision framework to detect text in CGImage"""
    request = Vision.VNRecognizeTextRequest.alloc().init()

    if fast_mode:
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelFast)
    else:
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
        cg_image, None
    )

    success = handler.performRequests_error_([request], None)

    if not success[0]:
        return []

    results = request.results()
    if not results:
        return []

    detected_texts = []
    for observation in results:
        top_candidate = observation.topCandidates_(1)[0]
        detected_texts.append(top_candidate.string())

    return detected_texts


def get_cropped_capture(client, scene_name, width, height):
    """Capture a scene with its transforms (crop, scale, etc.) applied"""
    try:
        response = client.get_source_screenshot(scene_name, "png", width, height, 100)
        return response
    except Exception as e:
        print(f"Error getting cropped capture: {e}")
        raise


def list_obs_sources(client):
    """List all available sources in OBS"""
    try:
        scenes = client.get_scene_list()
        print("\n=== Available Scenes ===")
        for scene in scenes.scenes:
            print(f"  - {scene['sceneName']}")

        print("\n=== Sources in current scene ===")
        current_scene = client.get_current_program_scene()
        print(f"Current scene: {current_scene.current_program_scene_name}")

        items = client.get_scene_item_list(current_scene.current_program_scene_name)
        for item in items.scene_items:
            print(f"  - {item['sourceName']} (ID: {item['sceneItemId']})")

    except Exception as e:
        print(f"Error listing sources: {e}")


def monitor_obs_source(
    source_name,
    scene_name,
    target_words,
    interval=0.5,
    obs_host="localhost",
    obs_port=4455,
    obs_password="your_password",
    cooldown=2.0,
    capture_width=640,
    capture_height=360,
    fast_mode=True,
    preview_window=None,
):
    """Monitor an OBS source/scene for specific words"""
    print(f"Connecting to OBS at {obs_host}:{obs_port}...")

    if isinstance(target_words, str):
        target_words = [target_words]

    sound_player = SoundPlayer()
    last_alert_time = 0

    try:
        client = obs.ReqClient(host=obs_host, port=obs_port, password=obs_password)
        print(f"✓ Connected to OBS")

        # List available sources
        list_obs_sources(client)

        print(f"\n=== Starting monitoring ===")
        print(f"Monitoring source: '{source_name}' in scene: '{scene_name}'")
        print(f"Resolution: {capture_width}x{capture_height}")
        print(f"OCR Mode: {'Fast' if fast_mode else 'Accurate'}")
        print(f"Looking for: {', '.join(target_words)}")
        print("Press Ctrl+C to stop\n")

        frame_count = 0
        while True:
            try:
                response = get_cropped_capture(
                    client, scene_name, capture_width, capture_height
                )

                img_data = base64.b64decode(response.image_data.split(",")[1])
                pil_image = Image.open(io.BytesIO(img_data))

                frame_count += 1

                if preview_window:
                    preview_window.updateImage_(pil_image)

                cg_image = pil_to_cgimage(pil_image)
                texts = detect_text_in_image(cg_image, fast_mode)

                all_text = " ".join(texts)
                if all_text:
                    print(all_text)

                found_words = []
                if all_text:
                    found_words = [
                        word
                        for word in target_words
                        if word.lower() in all_text.lower()
                    ]

                if found_words:
                    current_time = time.time()
                    if current_time - last_alert_time >= cooldown:
                        print(f"[{', '.join(found_words)}]")

                        threading.Thread(
                            target=sound_player.play_sound, daemon=True
                        ).start()

                        last_alert_time = current_time

            except Exception as e:
                print(f"Error capturing from OBS: {e}")
                import traceback

                traceback.print_exc()

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nMonitoring stopped")
        AppHelper.stopEventLoop()
    except Exception as e:
        print(f"Failed to connect to OBS: {e}")
        import traceback

        traceback.print_exc()
        AppHelper.stopEventLoop()


if __name__ == "__main__":
    # OBS Settings
    OBS_SOURCE_NAME = "Window Capture"
    OBS_SCENE_NAME = "Roblox"
    OBS_HOST = "localhost"
    OBS_PORT = 4455
    OBS_PASSWORD = "your_password"

    # Words to detect
    TARGET_WORDS = ["Exclusive", "Hacker"]

    # Performance settings
    COOLDOWN = 2.0
    CAPTURE_WIDTH = 640
    CAPTURE_HEIGHT = 480
    FAST_MODE = False

    # Initialize NSApplication
    app = NSApplication.sharedApplication()

    # Create preview window
    preview = PreviewWindow.alloc().initWithSize_((CAPTURE_WIDTH, CAPTURE_HEIGHT))
    preview.makeKeyAndOrderFront_(None)

    # Start monitoring in a separate thread
    monitor_thread = threading.Thread(
        target=monitor_obs_source,
        args=(OBS_SOURCE_NAME, OBS_SCENE_NAME, TARGET_WORDS),
        kwargs={
            "interval": 0.5,
            "obs_host": OBS_HOST,
            "obs_port": OBS_PORT,
            "obs_password": OBS_PASSWORD,
            "cooldown": COOLDOWN,
            "capture_width": CAPTURE_WIDTH,
            "capture_height": CAPTURE_HEIGHT,
            "fast_mode": FAST_MODE,
            "preview_window": preview,
        },
        daemon=True,
    )
    monitor_thread.start()

    # Run the application event loop
    AppHelper.runEventLoop()
