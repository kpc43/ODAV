import os
import subprocess
import numpy as np
import pygame
import threading
import queue
import time

# ==========================================
# AUDIO ENGINE
# ==========================================
class RobustAudioEngine:
    def __init__(self):
        self.max_center = 1500
        self.max_side = 900
        self.distances = {"left": 2000, "center": 2000, "right": 2000}
        self.is_speaking = False

        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        # center: low thump
        self.beep_center = self._generate_tone(freq=350, duration=0.08, vol=0.5, wave_type="sine")
        # sides: higher tick
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
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        if wave_type == "sine":
            wave = np.sin(2 * np.pi * freq * t)
        else:
            wave = np.sign(np.sin(2 * np.pi * freq * t))
        fade = np.linspace(1.0, 0.0, len(wave))
        wave = wave * fade * vol
        sound_array = np.zeros((len(wave), 2), dtype=np.int16)
        sound_array[:, 0] = (wave * 32767).astype(np.int16)
        sound_array[:, 1] = (wave * 32767).astype(np.int16)
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
                chan = pygame.mixer.find_channel()
                if chan:
                    if closest == "center":
                        chan.set_volume(0.8, 0.8)
                        chan.play(self.beep_center)
                    elif closest == "left":
                        chan.set_volume(1.0, 0.0)
                        chan.play(self.beep_side)
                    elif closest == "right":
                        chan.set_volume(0.0, 1.0)
                        chan.play(self.beep_side)
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
def run_live(audio_queue):
    audio = RobustAudioEngine()
    audio.speech_queue.put("system active")
    time.sleep(2)

    try:
        while True:
            try:
                data = audio_queue.get_nowait()
                audio.update_distances(
                    left_mm   = data["left"]   * 1000,
                    center_mm = data["center"] * 1000,
                    right_mm  = data["right"]  * 1000,
                )
            except queue.Empty:
                pass
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[System] Shutting down...")
        audio.shutdown()


if __name__ == "__main__":
    import sys
    if "--live" in sys.argv:
        # run with real ToF sensor
        from MainToF413 import run_tof
        audio_queue = queue.Queue()
        threading.Thread(target=run_tof, args=(audio_queue,), daemon=True).start()
        run_live(audio_queue)
    else:
        # run demo simulation
        run_simulation()
