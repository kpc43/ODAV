import os
import numpy as np
import pygame
import pyttsx3
import threading
import queue
import time
import math
import random

# ==========================================
# AUDIO ENGINE
# ==========================================
class SimulatedAudioEngine:
    def __init__(self, max_range_mm=2000):
        self.max_range = max_range_mm
        self.distances = {"left": self.max_range, "center": self.max_range, "right": self.max_range}
        
        # priority flag 
        self.is_speaking = False
        
        # initialize mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        # generate beep
        duration = 0.04
        t = np.linspace(0, duration, int(44100 * duration), False)
        wave = np.sin(2 * np.pi * 800 * t) * 0.3  # 800Hz tone at 30% volume
        
        sound_array = np.zeros((len(wave), 2), dtype=np.int16)
        sound_array[:, 0] = wave * 32767
        sound_array[:, 1] = wave * 32767
        self.beep_sound = pygame.sndarray.make_sound(sound_array)

        self.audio_folder = "sounds"
        self.loaded_voices = {}
        self._prepare_voices(["chair", "door", "person", "table", "audio simulation starting"])

        self.speech_queue = queue.Queue()
        self.last_announced = None
        self.last_ann_time = 0
        self.cooldown_seconds = 4

        self.running = True
        threading.Thread(target=self._voice_worker, daemon=True).start()
        threading.Thread(target=self._geiger_worker, daemon=True).start()
        print("[System] Simulation Audio Engine Ready (With Driver Fix).")

    def _prepare_voices(self, words_to_generate):
        """Generates .wav files using pyttsx3 and loads them into Pygame."""
        if not os.path.exists(self.audio_folder):
            os.makedirs(self.audio_folder)
            
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        
        for word in words_to_generate:
            filename = f"{word.replace(' ', '_')}.wav"
            file_path = os.path.join(self.audio_folder, filename)
            
            if not os.path.exists(file_path):
                text_to_speak = f"{word} ahead" if word != "audio simulation starting" else word
                engine.save_to_file(text_to_speak, file_path)
        
        engine.runAndWait()
        
        for word in words_to_generate:
            filename = f"{word.replace(' ', '_')}.wav"
            file_path = os.path.join(self.audio_folder, filename)
            self.loaded_voices[word] = pygame.mixer.Sound(file_path)

    def _voice_worker(self):
        """Plays the pre-generated voices purely through Pygame."""
        while self.running:
            try:
                label = self.speech_queue.get(timeout=0.5)
                label = label.lower()
                
                if label in self.loaded_voices:
                    print(f"\n🗣️ [AUDIO OUT] Announcing: '{label.upper()}'")
                    
                    # iverride counter
                    self.is_speaking = True
                    
                    chan = pygame.mixer.find_channel()
                    if chan:
                        chan.set_volume(1.0, 1.0)
                        chan.play(self.loaded_voices[label])
                        
                        # wait to finish voice
                        while chan.get_busy():
                            time.sleep(0.1)
                            
                    self.is_speaking = False # resume counter
                
                self.speech_queue.task_done()
            except queue.Empty:
                continue

    def _get_interval(self, mm):
        if mm < 100: return 0.05
        if mm >= self.max_range: return None
        return 0.05 + (mm / float(self.max_range))

    def _geiger_worker(self):
        """Plays the spatial beeps based on distance."""
        last_click = {"left": 0, "center": 0, "right": 0}
        while self.running:
            now = time.time()
            
            if self.is_speaking:
                time.sleep(0.05)
                continue
                
            for side, dist in self.distances.items():
                interval = self._get_interval(dist)
                
                if interval and (now - last_click[side] > interval):
                    chan = pygame.mixer.find_channel()
                    if chan:
                        if side == "left": chan.set_volume(1.0, 0.0)
                        elif side == "right": chan.set_volume(0.0, 1.0)
                        else: chan.set_volume(0.6, 0.6)
                        
                        chan.play(self.beep_sound)
                        last_click[side] = now
            time.sleep(0.01)

    def update_distances(self, left_mm, center_mm, right_mm):
        self.distances["left"] = left_mm
        self.distances["center"] = center_mm
        self.distances["right"] = right_mm

    def trigger_announcement(self, label):
        now = time.time()
        if (label != self.last_announced) or (now - self.last_ann_time > self.cooldown_seconds):
            self.speech_queue.put(label)
            self.last_announced = label
            self.last_ann_time = now

    def shutdown(self):
        self.running = False
        pygame.mixer.quit()

# ==========================================
# SIMULATION LOOP
# ==========================================
def run_simulation():
    print("\n==================================================")
    print("STARTING SENSOR & CAMERA SIMULATION")
    print("Press Ctrl+C to stop.")
    print("==================================================\n")
    
    audio = SimulatedAudioEngine()

    audio.speech_queue.put("audio simulation starting")
    time.sleep(2)
    
    start_time = time.time()
    
    try:
        while True:
            elapsed = time.time() - start_time
            
            # sim dist
            sim_left = 1050 + math.sin(elapsed) * 950
            sim_center = 1050 + math.sin(elapsed * 1.5) * 950
            sim_right = 2000 
            
            audio.update_distances(sim_left, sim_center, sim_right)
            
            # sim cam
            if random.random() < 0.015:
                mock_object = random.choice(["chair", "door", "person", "table"])
                print(f"\n[CAMERA SIM] Detected: {mock_object} in center frame.")
                audio.trigger_announcement(mock_object)
            
            # verify output
            if int(elapsed * 10) % 5 == 0:  
                print(f"[ToF SIM] Left: {sim_left:.0f}mm | Center: {sim_center:.0f}mm | Right: {sim_right:.0f}mm    ", end="\r")
                
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n[System] Stopping simulation...")
        audio.shutdown()

if __name__ == "__main__":
    run_simulation()