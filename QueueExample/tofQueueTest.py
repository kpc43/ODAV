from multiprocessing import Queue
import time

def tof(q: Queue):
    while True:
        sensorData = {
            "type": "sensor",
            "distance": 1.2
        }

        position = None

        data = q.get()

        if data["type"] == "vision":
            position = data["position"]
        
        print(f"Object at {position}")

        q.put(sensorData)
        time.sleep(0.5)