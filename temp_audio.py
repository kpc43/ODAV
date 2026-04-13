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
class RobustAudioEngine:
    def __init__(self):
        # prioritize center threats
        self.max_center = 1500 
        self.max_side = 900    
        self.distances = {"left": 2000, "center": 2000, "right": 2000}
        self.is_speaking = False

        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        # distinct tones for center vs sides
        # center: low frequency thump
        self.beep_center = self._generate_tone(freq=350, duration=0.08, vol=0.5, wave_type="sine")
        
        # sides: higher frequency tick
        self.beep_side = self._generate_tone(freq=1200, duration=0.02, vol=0.15, wave_type="square")

        # prep TTS voices
        self.audio_folder = "sounds"
        self.loaded_voices = {}
        self._prepare_voices(["chair", "door", "person", "table", "system active"])

        self.speech_queue = queue.Queue()
        self.last_announced = None
        self.last_ann_time = 0
        self.cooldown_seconds = 5 

        self.running = True
        threading.Thread(target=self._voice_worker, daemon=True).start()
        threading.Thread(target=self._geiger_worker, daemon=True).start()
        print("[System] Audio Engine Ready")

    def _generate_tone(self, freq, duration, vol, wave_type="sine"):
        """Generates sounds with different timbre."""
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        if wave_type == "sine":
            wave = np.sin(2 * np.pi * freq * t)
        else:
            wave = np.sign(np.sin(2 * np.pi * freq * t))
        fade = np.linspace(1.0, 0.0, len(wave))
        wave = wave * fade * vol
        sound_array = np.zeros((len(wave), 2), dtype=np.int16)
        sound_array[:, 0] = wave * 32767
        sound_array[:, 1] = wave * 32767
        return pygame.sndarray.make_sound(sound_array)

    def _prepare_voices(self, words_to_generate):
        """Generates .wav files using pyttsx3 and loads them."""
        if not os.path.exists(self.audio_folder):
            os.makedirs(self.audio_folder)
            
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        
        for word in words_to_generate:
            filename = f"{word.replace(' ', '_')}.wav"
            file_path = os.path.join(self.audio_folder, filename)
            if not os.path.exists(file_path):
                text_to_speak = f"{word} ahead" if word != "system active" else word
                engine.save_to_file(text_to_speak, file_path)
        engine.runAndWait()
        
        for word in words_to_generate:
            filename = f"{word.replace(' ', '_')}.wav"
            file_path = os.path.join(self.audio_folder, filename)
            self.loaded_voices[word] = pygame.mixer.Sound(file_path)

    def _voice_worker(self):
        """Plays the pre-generated voices."""
        while self.running:
            try:
                label = self.speech_queue.get(timeout=0.5)
                label = label.lower()
                
                if label in self.loaded_voices:
                    print(f"\n[AUDIO OUT] ANNOUNCEMENT: '{label.upper()}'")
                    
                    self.is_speaking = True
                    time.sleep(0.15)
                    chan = pygame.mixer.find_channel()
                    if chan:
                        chan.set_volume(1.0, 1.0)
                        chan.play(self.loaded_voices[label])
                        while chan.get_busy():
                            time.sleep(0.1)
                    time.sleep(0.15)
                    self.is_speaking = False 
                self.speech_queue.task_done()
            except queue.Empty:
                continue

    def _get_interval(self, mm):
        if mm < 200: return 0.08 
        if mm >= self.max_center: return None     
        normalized = (mm - 200) / (self.max_center - 200)
        return 0.08 + (normalized ** 2.5) * 1.5

    def _geiger_worker(self):
        """Plays only the closest, most dangerous threat."""
        last_click_time = 0
        
        while self.running:
            now = time.time()
            
            if self.is_speaking:
                time.sleep(0.05)
                continue
                
            # grab distance data and apply max thresholds
            dists = {
                "left": self.distances["left"] if self.distances["left"] < self.max_side else 2000,
                "center": self.distances["center"] if self.distances["center"] < self.max_center else 2000,
                "right": self.distances["right"] if self.distances["right"] < self.max_side else 2000
            }
            # distance padding to be safe
            weighted_dists = dists.copy()
            weighted_dists["center"] -= 250 
            
            # prioritize the closest threat
            closest_side = min(weighted_dists, key=weighted_dists.get)
            actual_dist = dists[closest_side] 
            
            interval = self._get_interval(actual_dist)
            
            if interval and actual_dist < 2000 and (now - last_click_time > interval):
                chan = pygame.mixer.find_channel()
                if chan:
                    if closest_side == "center":
                        chan.set_volume(0.8, 0.8)
                        chan.play(self.beep_center)
                    elif closest_side == "left":
                        chan.set_volume(1.0, 0.0)
                        chan.play(self.beep_side)
                    elif closest_side == "right":
                        chan.set_volume(0.0, 1.0)
                        chan.play(self.beep_side)
                        
                    last_click_time = now
                    
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
    audio = RobustAudioEngine()
    
    # test announcement
    audio.speech_queue.put("system active")
    time.sleep(2)
    start_time = time.time()
    
    try:
        while True:
            elapsed = time.time() - start_time
            
            # simulate distances
            sim_center = 1600 - (elapsed * 80) % 1400 
            sim_left = 800 + math.sin(elapsed * 2) * 400
            sim_right = 800 + math.cos(elapsed * 1.5) * 400
            
            audio.update_distances(sim_left, sim_center, sim_right)
            
            # simulate camera detection
            if random.random() < 0.01:
                mock_object = random.choice(["chair", "door"])
                print(f"\n[CAMERA SIM] Detected: {mock_object} in center frame.")
                audio.trigger_announcement(mock_object)
            
            # console visualization
            if int(elapsed * 10) % 5 == 0:  
                print(f"[RADAR] L: {sim_left:.0f}mm | C: {sim_center:.0f}mm | R: {sim_right:.0f}mm    ", end="\r")
                
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n[System] Shutting down...")
        audio.shutdown()

if __name__ == "__main__":
    run_simulation()