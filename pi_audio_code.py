import numpy as np
import sounddevice as sd
import pyttsx3
import time
import threading
import math
import random
from queue import Queue

# audio config
SAMPLE_RATE = 44100
BEEP_FREQ = 800
BEEP_DURATION = 0.04
MAX_VOL = 0.3

sd.default.device = 3
# pre-processing
t = np.linspace(0, BEEP_DURATION, int(SAMPLE_RATE * BEEP_DURATION), False)
beep_wave = np.sin(2 * np.pi * BEEP_FREQ * t) * MAX_VOL

def create_panned_beep(pos):
    stereo = np.zeros((len(beep_wave), 2), dtype=np.float32)
    if pos == "left": 
        stereo[:, 0] = beep_wave
    elif pos == "right": 
        stereo[:, 1] = beep_wave
    else:
        stereo[:, 0] = beep_wave * 0.7
        stereo[:, 1] = beep_wave * 0.7
    return stereo

beeps = {
    "left": create_panned_beep("left"), 
    "center": create_panned_beep("center"), 
    "right": create_panned_beep("right")
}

# tts queue
speech_queue = Queue()

def tts_worker():
    """Handles speech in the background."""
    engine = pyttsx3.init()
    engine.setProperty('rate', 160)
    engine.setProperty('volume', 0.9)
    
    while True:
        text = speech_queue.get()
        if text is None: break
        print(f"[TTS Audio] Speaking: '{text}'")
        engine.say(text)
        engine.runAndWait()
        speech_queue.task_done()

threading.Thread(target=tts_worker, daemon=True).start()

# mock data
def simulate_sensor_distances(current_time):
    """
    Simulates someone walking towards a wall on the left, 
    and an object approaching in the center.
    Returns distances in millimeters (0 to 2000).
    """
    # oscillation between 100mm and 2000mm
    dist_left = 1050 + math.sin(current_time * 0.5) * 950 
    dist_center = 1050 + math.sin(current_time * 0.8) * 950
    dist_right = 2000
    
    return {"left": dist_left, "center": dist_center, "right": dist_right}

def simulate_camera_detection(current_time):
    """Randomly selects an object every 5-10 seconds."""
    objects = ["Chair", "Table", "Door", "Person"]
    if random.random() < 0.01:
        return random.choice(objects)
    return None

# audio logic
def get_interval(mm):
    """Converts distance to beep delay."""
    if mm < 150: return 0.05 # rapid clicking
    if mm > 1900: return None # no click
    return 0.05 + (mm / 2000.0) # linear mapping from 0.05s to 0.15s

def run_standalone_test():
    print("\n--- AUDIO TEST ACTIVE ---")
    print("Listen for: Spatial beeps (Left/Center) getting faster/slower.")
    print("Listen for: Random TTS announcements interrupting.")
    print("Press Ctrl+C to stop.\n")
    
    last_click = {"left": 0, "center": 0, "right": 0}
    last_announced_obj = None
    last_ann_time = 0
    
    try:
        while True:
            now = time.time()
            
            # get mock data
            distances = simulate_sensor_distances(now)
            detected_object = simulate_camera_detection(now)
            
            # Geiger clicks
            for side, dist in distances.items():
                interval = get_interval(dist)
                if interval and (now - last_click[side] > interval):
                    sd.play(beeps[side], SAMPLE_RATE)
                    last_click[side] = now
            if detected_object:
                if (detected_object != last_announced_obj) or (now - last_ann_time > 4):
                    speech_queue.put(f"{detected_object} ahead")
                    last_announced_obj = detected_object
                    last_ann_time = now
            # delay
            time.sleep(0.02)
            
    except KeyboardInterrupt:
        print("\nTest Stopped.")

# start script
if __name__ == "__main__":
    speech_queue.put("Audio module test starting.")
    time.sleep(2)
    run_standalone_test()