import time
import threading
import queue
import pygame
import pyttsx3
import board
import busio
import adafruit_vl53l0x

# ==========================================
# 1. CENTRAL DATA HUB (Thread-Safe)
# ==========================================
class SystemHub:
    def __init__(self):
        # Distances in mm. Default is 2000 (out of range/silent)
        self.distances = {"left": 2000, "center": 2000, "right": 2000}
        self.speech_queue = queue.Queue()
        self.lock = threading.Lock()

    def update_distance(self, side, mm):
        with self.lock:
            self.distances[side] = mm

    def get_distances(self):
        with self.lock:
            return self.distances.copy()

    def announce_object(self, label):
        self.speech_queue.put(f"{label} ahead")

# ==========================================
# 2. TTS WORKER (Text-to-Speech Thread)
# ==========================================
def tts_worker(hub):
    """Runs in background, speaks whatever is in the queue."""
    engine = pyttsx3.init()
    engine.setProperty('rate', 160)
    engine.setProperty('volume', 1.0)
    
    print("[System] TTS Engine Ready.")
    while True:
        text = hub.speech_queue.get()
        if text is None: break
        
        # Optional: You could pause Pygame clicks here if you want total silence during speech
        print(f"[Audio] Announcing: {text}")
        engine.say(text)
        engine.runAndWait()
        hub.speech_queue.task_done()

# ==========================================
# 3. TOF SENSOR WORKER (Hardware Thread)
# ==========================================
def tof_worker(hub):
    """Polls the 3 sensors and updates the Hub."""
    i2c = busio.I2C(board.SCL, board.SDA)
    
    # IMPORTANT: Ensure these addresses match your hardware setup!
    try:
        sensors = {
            "left": adafruit_vl53l0x.VL53L0X(i2c, address=0x30),
            "center": adafruit_vl53l0x.VL53L0X(i2c, address=0x31),
            "right": adafruit_vl53l0x.VL53L0X(i2c, address=0x32)
        }
        print("[System] 3x ToF Sensors Initialized.")
    except ValueError as e:
        print(f"[Error] Sensor initialization failed. Check wiring and addresses: {e}")
        return

    while True:
        for name, sensor in sensors.items():
            if sensor.data_ready:
                dist = sensor.distance
                # VL53L0X returns 8190 or 0 when out of range
                if dist > 2000 or dist == 0: 
                    dist = 2000
                hub.update_distance(name, dist)
                sensor.clear_interrupt()
        time.sleep(0.01) # Prevent CPU pegging

# ==========================================
# 4. CAMERA WORKER (Object Detection Thread)
# ==========================================
def camera_worker(hub):
    """Handles object detection. Replace simulation with your actual code."""
    print("[System] Camera Module Ready.")
    last_announced_obj = None
    last_ann_time = 0
    COOLDOWN = 4 # Seconds before repeating the same object
    
    while True:
        now = time.time()
        
        # ---------------------------------------------------------
        # INSERT YOUR OBJECT DETECTION MODEL HERE
        # Example pseudo-code for your model:
        # frame = get_camera_frame()
        # label, x_center = your_model.detect(frame)
        # ---------------------------------------------------------
        
        # --- SIMULATION BLOCK (Remove when using real camera) ---
        label, x_center = None, 0.0
        import random
        if random.random() < 0.02: # 2% chance every loop to "see" something
            label = random.choice(["Chair", "Door"])
            x_center = 0.5 # Center of screen
        # ---------------------------------------------------------

        if label:
            # Check if object is in the middle 30% of the screen
            if 0.35 < x_center < 0.65:
                if (label != last_announced_obj) or (now - last_ann_time > COOLDOWN):
                    hub.announce_object(label)
                    last_announced_obj = label
                    last_ann_time = now
                    
        time.sleep(0.1) # Camera FPS pacing

# ==========================================
# 5. MAIN AUDIO ENGINE (Geiger Counter)
# ==========================================
def get_interval(mm):
    """Maps distance to delay interval. Closer = faster clicks."""
    if mm < 100: return 0.05      # Critical limit (fastest)
    if mm > 1500: return None     # Silent limit
    return 0.05 + (mm / 1500.0)

def main():
    hub = SystemHub()
    
    # Start all background threads
    threading.Thread(target=tts_worker, args=(hub,), daemon=True).start()
    threading.Thread(target=tof_worker, args=(hub,), daemon=True).start()
    threading.Thread(target=camera_worker, args=(hub,), daemon=True).start()
    
    # Initialize Pygame Audio for the PAM8403
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    
    try:
        click_sound = pygame.mixer.Sound("click.wav")
    except FileNotFoundError:
        print("[Error] 'click.wav' not found! Please place it in the same folder.")
        return

    last_click = {"left": 0, "center": 0, "right": 0}
    
    print("\n=======================================")
    print("ALL SYSTEMS NOMINAL. COMMENCING RADAR.")
    print("Press Ctrl+C to exit.")
    print("=======================================\n")
    
    try:
        while True:
            now = time.time()
            distances = hub.get_distances()
            
            for side, dist in distances.items():
                interval = get_interval(dist)
                
                if interval and (now - last_click[side] > interval):
                    # Find an open audio channel
                    chan = pygame.mixer.find_channel()
                    if chan:
                        # Pan the audio based on sensor position
                        if side == "left":
                            chan.set_volume(1.0, 0.0)
                        elif side == "right":
                            chan.set_volume(0.0, 1.0)
                        else: # center
                            chan.set_volume(0.6, 0.6)
                            
                        chan.play(click_sound)
                        last_click[side] = now
                        
            time.sleep(0.01) # Keeps the loop tight but doesn't max CPU
            
    except KeyboardInterrupt:
        print("\n[System] Shutting down gracefully...")
        pygame.mixer.quit()

if __name__ == "__main__":
    main()
