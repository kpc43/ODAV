import os
import subprocess
import numpy as np
import pygame
import threading
import queue
import time

from multiprocessing import Process

# ==========================================
# AUDIO ENGINE
# ==========================================
class RobustAudioEngine:
    def __init__(self):
        self.max_center = 1500
        self.max_side = 900
        self.distances = {"left": 2000, "center": 2000, "right": 2000}
        self.is_speaking = False

        # FIX 1: Increase buffer to 2048 to prevent audio dropouts/chirps
        pygame.mixer.init(frequency=48000, size=-16, channels=2, buffer=2048)
        
        # FIX 2: Increase total channels from the default 8 to 32
        pygame.mixer.set_num_channels(32)

        # center: low thump
        pygame.mixer.init(frequency=48000, size=-16, channels=2, buffer=2048)
        pygame.mixer.set_num_channels(32)

        # FIX: Explicitly reserve channels for specific tasks
        # Channel 0: Center, Channel 1: Left, Channel 2: Right, Channel 3: Voice
        self.chan_center = pygame.mixer.Channel(0)
        self.chan_left   = pygame.mixer.Channel(1)
        self.chan_right  = pygame.mixer.Channel(2)
        self.chan_voice  = pygame.mixer.Channel(3)

        # Re-generate tones with the "soft-square" logic from previous step
        self.beep_center = self._generate_tone(freq=350, duration=0.08, vol=0.5, wave_type="sine")
        self.beep_side = self._generate_tone(freq=1200, duration=0.02, vol=0.15, wave_type="square")
  
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
        sample_rate = 48000 # Updated to match the mixer
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        if wave_type == "sine":
            wave = np.sin(2 * np.pi * freq * t)
        else:
            # FIX 1: Use an "overdriven sine" instead of np.sign()
            # This creates a "soft" square wave with slightly rounded corners,
            # which drastically reduces the high-frequency aliasing chirps.
            wave = np.clip(np.sin(2 * np.pi * freq * t) * 5.0, -1.0, 1.0)
            
        # FIX 2: Create an envelope with a 2-millisecond fade-in.
        # This stops the speaker cone from snapping violently at t=0.
        fade_in_samples = int(sample_rate * 0.002) 
        envelope = np.ones_like(wave)
        
        if fade_in_samples < len(wave):
            envelope[:fade_in_samples] = np.linspace(0.0, 1.0, fade_in_samples)
            envelope[fade_in_samples:] = np.linspace(1.0, 0.0, len(wave) - fade_in_samples)
        else:
            # Fallback if duration is incredibly short
            envelope = np.linspace(1.0, 0.0, len(wave)) 
            
        wave = wave * envelope * vol
        
        # Scale to 16-bit signed integer maximum
        sound_array = np.zeros((len(wave), 2), dtype=np.int16)
        sound_array[:, 0] = (wave * 32766).astype(np.int16)
        sound_array[:, 1] = (wave * 32766).astype(np.int16)

        return pygame.sndarray.make_sound(sound_array)
    
    def _prepare_voices(self, words_to_generate):
        """Pre-generates .wav files using espeak-ng then loads into pygame."""
        if not os.path.exists(self.audio_folder):
            os.makedirs(self.audio_folder)

        for word in words_to_generate:
            filename = f"{word.replace(' ', '_')}.wav"
            file_path = os.path.join(self.audio_folder, filename)
            if not os.path.exists(file_path):
                text = f"{word} ahead" if word != "system active" else word
                print(f"[System] Generating voice for: '{text}'")
                subprocess.run(
                    ["espeak-ng", "-w", file_path, "-s", "160", "-a", "150", text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

        for word in words_to_generate:
            filename = f"{word.replace(' ', '_')}.wav"
            file_path = os.path.join(self.audio_folder, filename)
            if os.path.exists(file_path):
                self.loaded_voices[word] = pygame.mixer.Sound(file_path)
                print(f"[System] Loaded voice: '{word}'")
            else:
                print(f"[System] WARNING: Could not load voice for '{word}'")

    def _voice_worker(self):
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
        last_click_time = 0
        while self.running:
            now = time.time()
            if self.is_speaking:
                time.sleep(0.05)
                continue

            dists = {
                "left":   self.distances["left"]   if self.distances["left"]   < self.max_side   else 2000,
                "center": self.distances["center"] if self.distances["center"] < self.max_center else 2000,
                "right":  self.distances["right"]  if self.distances["right"]  < self.max_side   else 2000,
            }
            weighted = dists.copy()
            weighted["center"] -= 250  # prioritize center threats

            closest = min(weighted, key=weighted.get)
            actual_dist = dists[closest]
            interval = self._get_interval(actual_dist)

            if interval and actual_dist < 2000 and (now - last_click_time > interval):
                # FIX: Use dedicated channels instead of find_channel()
                if closest == "center":
                    self.chan_center.set_volume(0.8, 0.8)
                    self.chan_center.play(self.beep_center, fade_ms=5) # fade_ms prevents the pop
                elif closest == "left":
                    self.chan_left.set_volume(1.0, 0.0)
                    self.chan_left.play(self.beep_side, fade_ms=5)
                elif closest == "right":
                    self.chan_right.set_volume(0.0, 1.0)
                    self.chan_right.play(self.beep_side, fade_ms=5)
                
                last_click_time = now

            time.sleep(0.01)

    def update_distances(self, left_mm, center_mm, right_mm):
        self.distances["left"]   = left_mm
        self.distances["center"] = center_mm
        self.distances["right"]  = right_mm

    def trigger_announcement(self, label):
        now = time.time()
        if (label != self.last_announced) or (now - self.last_ann_time > self.cooldown_seconds):
            self.speech_queue.put(label)
            self.last_announced = label
            self.last_ann_time = now
            print(label)

    def shutdown(self):
        self.running = False
        pygame.mixer.quit()


# ==========================================
# SIMULATION LOOP (demo without ToF sensor)
# ==========================================
def run_simulation():
    audio = RobustAudioEngine()
    audio.speech_queue.put("system active")
    time.sleep(2)

    objects = ["chair", "door", "person", "table"]
    obj_index = 0
    last_obj_time = time.time()

    print("\n--- SIMULATION ACTIVE ---")
    print("Listen for: Beeps getting faster as objects get closer.")
    print("Listen for: Object announcements every 8 seconds.")
    print("Press Ctrl+C to stop.\n")

    try:
        start = time.time()
        while True:
            now = time.time()
            elapsed = now - start

            # cycle distance from 2000mm down to 100mm over 20s then reset
            cycle = elapsed % 20
            dist = 2000 - (cycle / 20) * 1900
            dist = max(100, dist)

            audio.update_distances(
                left_mm   = min(2000, dist + 100),
                center_mm = dist,
                right_mm  = min(2000, dist - 100),
            )

            # announce a new object every 8 seconds
            if now - last_obj_time > 8:
                audio.trigger_announcement(objects[obj_index % len(objects)])
                obj_index += 1
                last_obj_time = now

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[System] Shutting down...")
        audio.shutdown()


# ==========================================
# LIVE MODE (with ToF sensor)
# ==========================================
def run_live(audio_queue, video_queue):
    audio = RobustAudioEngine()
    audio.speech_queue.put("system active")
    time.sleep(2)

    last_obj_time = 0

    try:
        start = time.time()
        while True:
            now = time.time()
            try:
                data = audio_queue.get_nowait()
                audio.update_distances(
                    left_mm   = data["left"]   * 1000,
                    center_mm = data["center"] * 1000,
                    right_mm  = data["right"]  * 1000,
                )
            except queue.Empty:
                pass
            try:
                data = video_queue.get_nowait()
                # announce a new object every 15 seconds
                if now - last_obj_time > 15:
                    audio.trigger_announcement(data["object"])
                    last_obj_time = now
            except queue.Empty:
                pass
            time.sleep(0.05)


    except KeyboardInterrupt:
        print("\n[System] Shutting down...")
        audio.shutdown()


if __name__ == "__main__":
    import sys
    # if "--live" in sys.argv:
    # run with real ToF sensor
    from MainToF413 import run_tof
    audio_queue = queue.Queue()
    threading.Thread(target=run_tof, args=(audio_queue,), daemon=True).start()
    # run with camera
    from odavObjectDetectorFINAL import vision
    video_queue = queue.Queue()
    threading.Thread(target=vision, args=(video_queue,), daemon=True).start()


    run_live(audio_queue, video_queue)
    # else:
    #     # run demo simulation
    #     run_simulation()
