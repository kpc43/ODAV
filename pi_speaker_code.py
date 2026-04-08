import numpy as np
import sounddevice as sd
import soundfile as sf
import threading
import queue
import time
import os
import random
import pyttsx3
import board
import busio
import adafruit_vl53l0x

# ==========================================
# 1. THE MODERN AUDIO ENGINE (Pi 5 Compatible)
# ==========================================
class ModernAudioEngine:
    def __init__(self, click_file="click.wav", max_range_mm=2000):
        self.max_range = max_range_mm
        self.distances = {"left": self.max_range, "center": self.max_range, "right": self.max_range}
        
        try:
            self.click_data, self.fs = sf.read(click_file, dtype='float32')
            if len(self.click_data.shape) == 1:
                self.click_data = np.column_stack((self.click_data, self.click_data))
        except FileNotFoundError:
            print(f"[ERROR] Could not find '{click_file}'.")
            self.click_data = None
            self.fs = 44100

        # prepare audio files
        self.audio_folder = "sounds"
        self.audio_mapping = {
            "chair": "chair.wav", "person": "person.wav", "door": "door.wav",
            "stairs": "stairs.wav", "table": "table.wav", "wall": "wall.wav"
        }
        self.loaded_voices = {}
        self._prepare_announcement_files()

        self.speech_queue = queue.Queue()
        self.last_announced = None
        self.last_ann_time = 0
        self.cooldown_seconds = 4

        self.running = True
        threading.Thread(target=self._voice_worker, daemon=True).start()
        threading.Thread(target=self._geiger_worker, daemon=True).start()
        print("[System] Audio engine initialized.")

    def _prepare_announcement_files(self):
        if not os.path.exists(self.audio_folder):
            os.makedirs(self.audio_folder)
            
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        
        # generate tts files
        for obj, filename in self.audio_mapping.items():
            file_path = os.path.join(self.audio_folder, filename)
            if not os.path.exists(file_path):
                engine.save_to_file(f"{obj} ahead", file_path)
        engine.runAndWait()
        
        # load .wav files
        for obj, filename in self.audio_mapping.items():
            file_path = os.path.join(self.audio_folder, filename)
            data, fs = sf.read(file_path, dtype='float32')
            if len(data.shape) == 1:
                data = np.column_stack((data, data))
            self.loaded_voices[obj.lower()] = (data, fs)

    def _play_panned(self, data, sample_rate, side="center"):
        """Mathematically pans the audio by muting the opposite channel."""
        panned_data = data.copy()
        if side == "left":
            panned_data[:, 1] = 0.0 # mute right
        elif side == "right":
            panned_data[:, 0] = 0.0 # mute left
        else:
            panned_data *= 0.6
            
        # Play non-blocking
        sd.play(panned_data, sample_rate)

    def _voice_worker(self):
        """Plays voice arrays directly without stopping the rest of the script."""
        while self.running:
            try:
                label = self.speech_queue.get(timeout=0.5)
                if label in self.loaded_voices:
                    data, fs = self.loaded_voices[label]
                    print(f"[Audio] Announcing: {label.upper()} AHEAD")
                    
                    sd.play(data, fs)
                    sd.wait()
                    
                self.speech_queue.task_done()
            except queue.Empty:
                continue

    def _get_interval(self, mm):
        if mm < 100: return 0.05
        if mm >= self.max_range: return None
        return 0.05 + (mm / float(self.max_range))

    def _geiger_worker(self):
        """Triggers the mathematical audio clicks based on distance."""
        last_click = {"left": 0, "center": 0, "right": 0}
        while self.running:
            now = time.time()
            if self.click_data is None:
                time.sleep(1)
                continue
                
            for side, dist in self.distances.items():
                interval = self._get_interval(dist)
                if interval and (now - last_click[side] > interval):
                    self._play_panned(self.click_data, self.fs, side)
                    last_click[side] = now
            time.sleep(0.01)

    def update_tof(self, left_mm, center_mm, right_mm):
        self.distances["left"] = left_mm if (0 < left_mm < self.max_range) else self.max_range
        self.distances["center"] = center_mm if (0 < center_mm < self.max_range) else self.max_range
        self.distances["right"] = right_mm if (0 < right_mm < self.max_range) else self.max_range

    def process_camera_detection(self, label, x_center):
        now = time.time()
        label = label.lower()
        if label not in self.loaded_voices: return
        
        # center of frame
        if 0.35 < x_center < 0.65:
            if (label != self.last_announced) or (now - self.last_ann_time > self.cooldown_seconds):
                self.speech_queue.put(label)
                self.last_announced = label
                self.last_ann_time = now

    def shutdown(self):
        self.running = False
        sd.stop()

# ==========================================
# CAMERA MODULE
# ==========================================
def camera_worker(audio_engine):
    print("[System] Camera module initialized.")
    while True:
        # ---------------------------------------------------------
        # INSERT CV MODULE CODE HERE:
        # frame = camera.read()
        # label, x_center = your_model.predict(frame)
        # ---------------------------------------------------------
        
        # --- MOCK SIMULATION ---
        label, x_center = None, 0.0
        if random.random() < 0.02: # 2% chance to "see" something
            label = random.choice(["chair", "door", "table"])
            x_center = 0.5 
        # ---------------------------------------------------------

        if label:
            audio_engine.process_camera_detection(label, x_center)
            
        time.sleep(0.1) # prevent CPU hogging

# ==========================================
# MAIN HARDWARE LOOP
# ==========================================
def main():
    audio = ModernAudioEngine(click_file="click.wav")
    
    # start camera thread
    threading.Thread(target=camera_worker, args=(audio,), daemon=True).start()
    
    # initialize i2c
    i2c = busio.I2C(board.SCL, board.SDA)
    try:
        sensors = {
            "left": adafruit_vl53l0x.VL53L0X(i2c, address=0x30),
            "center": adafruit_vl53l0x.VL53L0X(i2c, address=0x31),
            "right": adafruit_vl53l0x.VL53L0X(i2c, address=0x32)
        }
        for s in sensors.values():
            s.start_ranging()
        print("[System] ToF modules initialized.")
    except Exception as e:
        print(f"\n[ERROR] Could not connect to ToF sensors: {e}")
        audio.shutdown()
        return

    print("\n>>> SYSTEM ACTIVE <<<\n")
    
    try:
        while True:
            # poll each sensor
            dist_l = sensors["left"].distance if sensors["left"].data_ready else 2000
            dist_c = sensors["center"].distance if sensors["center"].data_ready else 2000
            dist_r = sensors["right"].distance if sensors["right"].data_ready else 2000
            
            # clear interrupts
            for s in sensors.values():
                if s.data_ready:
                    s.clear_interrupt()

            # push data
            audio.update_tof(dist_l, dist_c, dist_r)
            
            time.sleep(0.01) 
            
    except KeyboardInterrupt:
        print("\n[System] Shutting down gracefully...")
        for s in sensors.values():
            s.stop_ranging()
        audio.shutdown()

if __name__ == "__main__":
    main()