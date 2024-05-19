import cv2
from mss import mss
import numpy as np
import pyautogui
import time
from pynput import keyboard
import threading
import pygetwindow as gw

print("Detecting window...")

# detect window
def get_window_region(title):
    try:
        win = gw.getWindowsWithTitle(title)[0]
        if win:
            return (win.left, win.top, win.width, win.height)
    except IndexError:
        print("Window not found")
        return None
window_title = "McOsu"
window_region = get_window_region(window_title)
if window_region:
    print(f"Window found at: {window_region}")
    default_region = window_region
else:
    print("Using default region")
    default_region = (0, 0, 1280, 720)

print("Starting...")
print("Press 'q' to toggle clicking on/off")
print("Press 'ESC' to exit")

clicking_enabled = False 

exit_event = threading.Event()

def on_press(key):
    global clicking_enabled
    if key == keyboard.Key.shift:
        exit_event.set()
        print("Exiting...")
        return False
    try:
        if key.char == 'q':
            clicking_enabled = not clicking_enabled
            print("Clicking is now", "enabled" if clicking_enabled else "disabled")
    except AttributeError:
        pass 

# keyboard listener
listener = keyboard.Listener(on_press=on_press)
listener.start()

# capture screen
def capture_screen(region=None):
    with mss() as sct:
        # take screenshot
        monitor = {"top": region[1], "left": region[0], "width": region[2], "height": region[3]} if region else sct.monitors[1]
        sct_img = sct.grab(monitor)
        # convert to a numpy array
        frame = np.array(sct_img)
        # convert colors from BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame

default_region = (2560 - 1280, 0, 1280, 720)
last_detected_circles = None

def calculate_new_roi(last_circle, margin=100, screen_width=1280, screen_height=720):
    if last_circle is None:
        return default_region
    x, y, r = last_circle
    screen_x_offset = 2560 - 1280
    screen_y_offset = 0

    left = max(screen_x_offset, x - margin + screen_x_offset)
    top = max(screen_y_offset, y - margin + screen_y_offset)

    right = min(screen_x_offset + screen_width, left + 2 * margin)
    bottom = min(screen_y_offset + screen_height, top + 2 * margin)

    width = right - left
    height = bottom - top

    if width <= 0 or height <= 0 or left < screen_x_offset or top < screen_y_offset:
        return default_region
    return (left, top, width, height)

# detect circles
def detect_circles(frame, cursor_radius=40, radius_tolerance=3):
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #  gaussian blur
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    # adaptive threshold
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    # find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        # approx contour
        (x, y), radius = cv2.minEnclosingCircle(contour)
        if cursor_radius - radius_tolerance < radius < cursor_radius + radius_tolerance:
            return np.array([[[int(x), int(y), radius]]], dtype=np.uint16)
    # Detect circles
    circles = cv2.HoughCircles(thresh, cv2.HOUGH_GRADIENT, 1, 20, param1=50, param2=30, minRadius=20, maxRadius=0)
    if circles is not None:
        filtered_circles = []
        for circle in circles[0, :]:
            _, _, r = circle
            # exclude circles with a radius within the range of the cursor radius
            if not (cursor_radius - radius_tolerance < r < cursor_radius + radius_tolerance):
                filtered_circles.append(circle)
        if filtered_circles:
            return np.array([filtered_circles], dtype=np.uint16)
    return None

last_click_time = 0
click_interval = 0.1 # this will limit the accuracy of the bot, but its better than my pc blowing up (for now).

# main loop
while not exit_event.is_set():
    if clicking_enabled:
        if last_detected_circles:
            region = calculate_new_roi(last_detected_circles)
        else:
            region = default_region

        frame = capture_screen(region=region)
        circles = detect_circles(frame)

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for circle in circles[0, :]:
                x, y, r = circle
                target_x, target_y = x + region[0], y + region[1]
                # update last detected circles
                last_detected_circles = (target_x, target_y, r)

                # check if time to click 
                if time.time() - last_click_time > click_interval:
                    print(f"Detected target at: {target_x}, {target_y}") 
                    pyautogui.moveTo(target_x, target_y)
                    pyautogui.click()
                    print("Clicked!") 
                    last_click_time = time.time()
    exit_event.wait(0.1)

listener.join()
