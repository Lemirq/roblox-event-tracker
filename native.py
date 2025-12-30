import io
import signal
import sys
import threading
import time
from collections import deque

import objc
import Quartz
import Vision
from AppKit import (
    NSApplication,
    NSBeep,
    NSImage,
    NSImageView,
    NSSound,
    NSWindow,
)
from Foundation import NSData, NSMakeRect
from PIL import Image
from PyObjCTools import AppHelper


class PerformanceMonitor:
    """Track and display performance metrics"""

    def __init__(self, window_size=30):
        self.window_size = window_size
        self.frame_times = deque(maxlen=window_size)
        self.capture_times = deque(maxlen=window_size)
        self.ocr_times = deque(maxlen=window_size)
        self.conversion_times = deque(maxlen=window_size)
        self.crop_times = deque(maxlen=window_size)
        self.total_frames = 0
        self.start_time = time.time()
        self.last_stats_time = time.time()
        self.stats_interval = 5.0

    def record_frame(self, capture_time=0, ocr_time=0, conversion_time=0, crop_time=0):
        self.frame_times.append(time.time())
        self.capture_times.append(capture_time)
        self.ocr_times.append(ocr_time)
        self.conversion_times.append(conversion_time)
        self.crop_times.append(crop_time)
        self.total_frames += 1

    def get_fps(self):
        if len(self.frame_times) < 2:
            return 0
        duration = self.frame_times[-1] - self.frame_times[0]
        return (len(self.frame_times) - 1) / duration if duration > 0 else 0

    def get_average_times(self):
        def avg(d):
            return sum(d) / len(d) if d else 0

        return {
            "capture": avg(self.capture_times),
            "ocr": avg(self.ocr_times),
            "conversion": avg(self.conversion_times),
            "crop": avg(self.crop_times),
        }

    def print_stats(self):
        now = time.time()
        if now - self.last_stats_time < self.stats_interval:
            return

        self.last_stats_time = now

        fps = self.get_fps()
        times = self.get_average_times()
        total_avg = sum(times.values())

        elapsed = now - self.start_time
        print(
            f"\n=== Performance Stats ==="
            f"\nFrames: {self.total_frames} | FPS: {fps:.2f}"
            f"\nAvg times (ms): Capture={times['capture'] * 1000:.1f} "
            f"Crop={times['crop'] * 1000:.1f} "
            f"Convert={times['conversion'] * 1000:.1f} "
            f"OCR={times['ocr'] * 1000:.1f} "
            f"Total={total_avg * 1000:.1f}"
            f"\nUptime: {elapsed / 60:.1f}min\n"
        )


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

        self.setTitle_("Window Capture Preview")
        self.setLevel_(1)

        self.image_view = NSImageView.alloc().initWithFrame_(
            NSMakeRect(0, 0, width, height)
        )
        self.image_view.setImageScaling_(3)  # NSImageScaleProportionallyUpOrDown
        self.setContentView_(self.image_view)
        self.setAspectRatio_((width, height))

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
        if ns_image:
            self.setAspectRatio_(ns_image.size())


def list_windows():
    """List all available windows on the system"""
    print("\n=== Available Windows ===")

    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )

    for i, window in enumerate(window_list):
        window_id = window.get("kCGWindowNumber", "N/A")
        window_name = window.get("kCGWindowName", "")
        owner_name = window.get("kCGWindowOwnerName", "")
        bounds = window.get("kCGWindowBounds", {})

        if window_name or owner_name:
            print(
                f"  [{i}] ID: {window_id} | "
                f"Owner: {owner_name} | "
                f"Name: {window_name} | "
                f"Size: {bounds.get('Width', 0):.0f}x{bounds.get('Height', 0):.0f}"
            )

    print()


def find_window_by_name(window_name_substring):
    """Find a window ID by partial name match"""
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )

    matches = []
    for window in window_list:
        window_id = window.get("kCGWindowNumber")
        name = window.get("kCGWindowName", "")
        owner = window.get("kCGWindowOwnerName", "")

        full_name = f"{owner} - {name}"
        if window_name_substring.lower() in full_name.lower():
            matches.append(
                {
                    "id": window_id,
                    "name": name,
                    "owner": owner,
                    "bounds": window.get("kCGWindowBounds", {}),
                }
            )

    return matches


def capture_window(window_id):
    """Capture a specific window by its ID"""
    try:
        cg_image = Quartz.CGWindowListCreateImage(
            Quartz.CGRectNull,
            Quartz.kCGWindowListOptionIncludingWindow,
            window_id,
            Quartz.kCGWindowImageBoundsIgnoreFraming
            | Quartz.kCGWindowImageNominalResolution,
        )

        if cg_image is None:
            return None

        return cg_image

    except Exception as e:
        print(f"Error capturing window: {e}")
        return None


def crop_cgimage(cg_image, crop_rect):
    """Crop a CGImage to the specified rectangle

    Args:
        cg_image: The CGImage to crop
        crop_rect: Dictionary with 'x', 'y', 'width', 'height' keys
    """
    try:
        rect = Quartz.CGRectMake(
            crop_rect["x"], crop_rect["y"], crop_rect["width"], crop_rect["height"]
        )

        cropped = Quartz.CGImageCreateWithImageInRect(cg_image, rect)
        return cropped
    except Exception as e:
        print(f"Error cropping image: {e}")
        return cg_image


def calculate_crop_region(
    full_width, full_height, h_start=1 / 3, h_end=2 / 3, v_start=0, v_end=0.5
):
    """Calculate crop region based on percentages

    Args:
        full_width: Full image width
        full_height: Full image height
        h_start: Horizontal start position (0-1, default 1/3 for middle third)
        h_end: Horizontal end position (0-1, default 2/3 for middle third)
        v_start: Vertical start position (0-1, default 0 for top)
        v_end: Vertical end position (0-1, default 0.5 for top half)

    Returns:
        Dictionary with x, y, width, height
    """
    x = int(full_width * h_start)
    y = int(full_height * v_start)
    width = int(full_width * (h_end - h_start))
    height = int(full_height * (v_end - v_start))

    return {"x": x, "y": y, "width": width, "height": height}


def downscale_cgimage(cg_image, scale_factor=0.5):
    """Downscale a CGImage by the given factor for faster processing

    Args:
        cg_image: The CGImage to downscale
        scale_factor: Factor to scale by (0.5 = half size)

    Returns:
        Downscaled CGImage
    """
    width = Quartz.CGImageGetWidth(cg_image)
    height = Quartz.CGImageGetHeight(cg_image)

    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    color_space = Quartz.CGImageGetColorSpace(cg_image)
    context = Quartz.CGBitmapContextCreate(
        None,
        new_width,
        new_height,
        8,  # bits per component
        0,  # bytes per row (auto)
        color_space,
        Quartz.kCGImageAlphaPremultipliedFirst | Quartz.kCGBitmapByteOrder32Little,
    )

    if context is None:
        return cg_image

    Quartz.CGContextSetInterpolationQuality(context, Quartz.kCGInterpolationLow)
    Quartz.CGContextDrawImage(
        context, Quartz.CGRectMake(0, 0, new_width, new_height), cg_image
    )

    scaled_image = Quartz.CGBitmapContextCreateImage(context)
    return scaled_image if scaled_image else cg_image


def cgimage_to_pil(cg_image):
    """Convert CGImage to PIL Image"""
    width = Quartz.CGImageGetWidth(cg_image)
    height = Quartz.CGImageGetHeight(cg_image)
    bytes_per_row = Quartz.CGImageGetBytesPerRow(cg_image)

    data_provider = Quartz.CGImageGetDataProvider(cg_image)
    data = Quartz.CGDataProviderCopyData(data_provider)

    # macOS captures in BGRA format
    pil_image = Image.frombytes(
        "RGBA", (width, height), data, "raw", "BGRA", bytes_per_row
    )

    return pil_image


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


def monitor_window(
    window_identifier,
    target_words,
    interval=0.5,
    cooldown=2.0,
    fast_mode=True,
    preview_window=None,
    crop_h_start=1 / 3,
    crop_h_end=2 / 3,
    crop_v_start=0,
    crop_v_end=0.5,
    scale_factor=0.5,
):
    """Monitor a window for specific words

    Args:
        crop_h_start: Horizontal crop start (0-1, default 1/3)
        crop_h_end: Horizontal crop end (0-1, default 2/3)
        crop_v_start: Vertical crop start (0-1, default 0 for top)
        crop_v_end: Vertical crop end (0-1, default 0.5 for top half)
        scale_factor: Scale factor for downscaling (0.5 = half size, 1.0 = no scaling)
    """

    if isinstance(target_words, str):
        target_words = [target_words]

    sound_player = SoundPlayer()
    last_alert_time = 0
    perf_monitor = PerformanceMonitor(window_size=30)

    try:
        # Find the window
        print(f"Searching for window: '{window_identifier}'...")

        # Try as window ID first (if it's a number)
        window_id = None
        try:
            window_id = int(window_identifier)
            print(f"✓ Using window ID: {window_id}")
        except ValueError:
            # Search by name
            matches = find_window_by_name(window_identifier)

            if not matches:
                print(f"❌ No windows found matching '{window_identifier}'")
                list_windows()
                return

            if len(matches) > 1:
                print(f"⚠ Found {len(matches)} matching windows:")
                for i, match in enumerate(matches):
                    print(f"  [{i}] {match['owner']} - {match['name']}")
                print(
                    "Using the first match. Specify window ID to choose a specific one."
                )

            window_id = matches[0]["id"]
            print(
                f"✓ Found window: {matches[0]['owner']} - {matches[0]['name']} "
                f"(ID: {window_id})"
            )

        print(f"\n=== Starting monitoring ===")
        print(f"Window ID: {window_id}")
        print(
            f"Crop Region: H[{crop_h_start:.1%}-{crop_h_end:.1%}] V[{crop_v_start:.1%}-{crop_v_end:.1%}]"
        )
        print(f"Scale Factor: {scale_factor:.0%}")
        print(f"OCR Mode: {'Fast' if fast_mode else 'Accurate'}")
        print(f"Looking for: {', '.join(target_words)}")
        print("Press Ctrl+C to stop\n")

        frame_count = 0
        consecutive_failures = 0
        max_failures = 10

        while True:
            try:
                capture_start = time.time()

                cg_image = capture_window(window_id)

                if cg_image is None:
                    consecutive_failures += 1
                    print(
                        f"⚠ Failed to capture window "
                        f"({consecutive_failures}/{max_failures})"
                    )

                    if consecutive_failures >= max_failures:
                        print(
                            "Too many failures. Window may have been closed. "
                            "Searching again..."
                        )

                        if isinstance(window_identifier, str):
                            matches = find_window_by_name(window_identifier)
                            if matches:
                                window_id = matches[0]["id"]
                                print(f"✓ Re-found window (ID: {window_id})")
                                consecutive_failures = 0
                            else:
                                print("❌ Window no longer exists")
                                break
                        else:
                            print("❌ Window no longer exists")
                            break

                    time.sleep(1)
                    continue

                consecutive_failures = 0
                capture_time = time.time() - capture_start

                # Crop the image
                crop_start = time.time()

                full_width = Quartz.CGImageGetWidth(cg_image)
                full_height = Quartz.CGImageGetHeight(cg_image)

                crop_rect = calculate_crop_region(
                    full_width,
                    full_height,
                    crop_h_start,
                    crop_h_end,
                    crop_v_start,
                    crop_v_end,
                )

                cropped_cg_image = crop_cgimage(cg_image, crop_rect)

                # Downscale for faster OCR processing
                if scale_factor < 1.0:
                    cropped_cg_image = downscale_cgimage(cropped_cg_image, scale_factor)

                crop_time = time.time() - crop_start

                conversion_start = time.time()

                pil_image = cgimage_to_pil(cropped_cg_image)

                if preview_window:
                    preview_window.updateImage_(pil_image)

                conversion_time = time.time() - conversion_start

                ocr_start = time.time()

                texts = detect_text_in_image(cropped_cg_image, fast_mode)

                ocr_time = time.time() - ocr_start

                perf_monitor.record_frame(
                    capture_time, ocr_time, conversion_time, crop_time
                )

                frame_count += 1

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

                perf_monitor.print_stats()

            except Exception as e:
                print(f"Error processing frame: {e}")
                import traceback

                traceback.print_exc()

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nMonitoring stopped")
        perf_monitor.print_stats()
    except Exception as e:
        print(f"Error in monitoring: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Window to capture
    WINDOW_NAME = "14488"

    # Words to detect
    TARGET_WORDS = ["Exclusive", "Hacker"]

    # Crop settings (0.0 to 1.0)
    # Horizontal: middle third (left 1/3 to right 2/3)
    CROP_H_START = 1 / 3
    CROP_H_END = 2 / 3

    # Vertical: top half (top 0% to 50%)
    CROP_V_START = 1 / 8
    CROP_V_END = 0.5

    # Performance settings
    COOLDOWN = 2.0
    FAST_MODE = False
    SCALE_FACTOR = 0.5  # Downscale to 50% for faster OCR

    # List all windows first
    list_windows()

    # Initialize NSApplication
    app = NSApplication.sharedApplication()

    # Create preview window (will show cropped region)
    preview = PreviewWindow.alloc().initWithSize_((640, 480))
    preview.makeKeyAndOrderFront_(None)

    # Start monitoring in a separate thread
    monitor_thread = threading.Thread(
        target=monitor_window,
        args=(WINDOW_NAME, TARGET_WORDS),
        kwargs={
            "interval": 1,
            "cooldown": COOLDOWN,
            "fast_mode": FAST_MODE,
            "preview_window": preview,
            "crop_h_start": CROP_H_START,
            "crop_h_end": CROP_H_END,
            "crop_v_start": CROP_V_START,
            "crop_v_end": CROP_V_END,
            "scale_factor": SCALE_FACTOR,
        },
        daemon=True,
    )
    monitor_thread.start()

    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\nQuitting...")
        AppHelper.stopEventLoop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Run the application event loop (installMachInterrupt=False to avoid spurious signals)
    try:
        AppHelper.runEventLoop(installInterrupt=False)
    except KeyboardInterrupt:
        pass
