import threading
import time

from pynput import keyboard, mouse

CLICK_DELAY = 0.01


class AutoClicker:
    def __init__(self):
        self.clicking = False
        self.mouse_controller = mouse.Controller()
        self.pressed_keys = set()

    def click_loop(self):
        while True:
            if self.clicking:
                self.mouse_controller.click(mouse.Button.left)
                time.sleep(CLICK_DELAY)
            else:
                time.sleep(0.05)

    def on_press(self, key):
        self.pressed_keys.add(key)

        if keyboard.Key.alt_l in self.pressed_keys or keyboard.Key.alt_r in self.pressed_keys:
            if key == keyboard.KeyCode.from_char("x"):
                self.clicking = not self.clicking
                print("ON" if self.clicking else "OFF")
                time.sleep(0.2)

    def on_release(self, key):
        self.pressed_keys.discard(key)

    def run(self):
        threading.Thread(target=self.click_loop, daemon=True).start()
        print("AutoClicker running. Press Alt+X to toggle.")
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()


if __name__ == "__main__":
    AutoClicker().run()
