from multiprocessing import Queue
import time
from getSensorDistanceNoTof import getSensorDistanceNoTof

SENSOR_IDS = [1, 2, 3]
POLL_INTERVAL = 0.5

def tof(tof_queue: Queue, sensor_id: int):
    
    #Message format: {"sensor_id": int, "distance": float}
    
    while True:
        distance = getSensorDistanceNoTof(sensor_id)
        tof_queue.put({
            "sensor_id": sensor_id,
            "distance": distance
        })
        time.sleep(POLL_INTERVAL)