from getSensorDistanceNoTof import getSensorDistanceNoTof
from queue import Queue, Empty
import time
import threading

VL             = [1, 2, 3]
MSR            = 2.0
POLL_INTERVAL  = 0.5
PRINT_INTERVAL = 1.0

SENSOR_LABELS = {
    1: "left",
    2: "center",
    3: "right",
}

def tof_worker(tof_queue: Queue, sensor_id: int):
    while True:
        distance = getSensorDistanceNoTof(sensor_id)
        tof_queue.put({"sensor_id": sensor_id, "distance": distance})
        time.sleep(POLL_INTERVAL)

def run_tof(audio_queue: Queue):
    tof_queue = Queue()
    SD = {sid: MSR + 1 for sid in VL}
    sensor_status = {
        1: {"label": "left",   "distance": MSR + 1},
        2: {"label": "center", "distance": MSR + 1},
        3: {"label": "right",  "distance": MSR + 1},
    }

    for sensor_id in VL:
        threading.Thread(target=tof_worker, args=(tof_queue, sensor_id), daemon=True).start()

    print("TOF sensors running\n")
    last_print_time = time.time()

    while True:
        try:
            while True:
                msg = tof_queue.get_nowait()
                SD[msg["sensor_id"]] = msg["distance"]
        except Empty:
            pass

        current_time = time.time()
        if current_time - last_print_time >= PRINT_INTERVAL:

            for sid in VL:
                sensor_status[sid]["distance"] = SD[sid]
                print(f"[Sensor {sid} | {SENSOR_LABELS[sid].upper()}] {SD[sid]:.2f} m")

            audio_queue.put({
                "left":   SD[1],
                "center": SD[2],
                "right":  SD[3],
            })
            last_print_time = current_time

        time.sleep(0.05)