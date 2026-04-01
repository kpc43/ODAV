from multiprocessing import Queue
import time

def vision(q: Queue):
    while True:
        detection = {
            "type": "vision",
            "object": "Exit Sign",
            "confidence": 0.67,
            "position": [[12, 24], [36, 48]]
        }

        q.put(detection)
        time.sleep(0.5)