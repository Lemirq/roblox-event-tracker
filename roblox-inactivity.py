import random
import time

import pyautogui

pyautogui.FAILSAFE = True


class AntiIdle:
    def __init__(self):
        self.actions = [
            self.human_mouse_move,
            self.random_jump,
            self.random_walk,
            self.rotate_camera,
        ]

    def human_mouse_move(self):
        x, y = pyautogui.position()
        new_x = x + random.randint(-50, 50)
        new_y = y + random.randint(-50, 50)
        pyautogui.moveTo(new_x, new_y, duration=random.uniform(0.1, 0.5))

    def random_jump(self):
        print("Action: Jumping")
        pyautogui.press("space")

    def random_walk(self):
        keys = ["w", "a", "s", "d"]
        key = random.choice(keys)
        duration = random.uniform(0.1, 0.8)
        print(f"Action: Walking ({key}) for {duration:.2f}s")
        pyautogui.keyDown(key)
        time.sleep(duration)
        pyautogui.keyUp(key)

    def rotate_camera(self):
        keys = ["left", "right"]
        key = random.choice(keys)
        duration = random.uniform(0.2, 0.6)
        print(f"Action: Rotating Camera ({key})")
        pyautogui.keyDown(key)
        time.sleep(duration)
        pyautogui.keyUp(key)

    def run(self):
        print("--- REALISTIC ANTI-IDLE STARTED ---")
        print("Press Ctrl+C or move mouse to top-left corner to stop.")
        print("Switch to your Roblox window now!")
        time.sleep(5)

        try:
            while True:
                wait_time = random.randint(120, 240)
                print(f"Sleeping for {wait_time} seconds...")
                time.sleep(wait_time)

                action = random.choice(self.actions)
                action()

                if random.random() > 0.7:
                    print("Performing double action...")
                    time.sleep(random.uniform(0.5, 1.5))
                    self.random_jump()

        except KeyboardInterrupt:
            print("\nScript stopped by user.")


if __name__ == "__main__":
    AntiIdle().run()
