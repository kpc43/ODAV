from multiprocessing import Process, Queue
import time

from getObjInfoNoCam import getObjInfoNoCam
from getSensorDistanceTof import getSensorDistanceTof
from tofQueueTest import tof, SENSOR_IDS

MSR = 2.0           # Max Sensor Range (meters)
TOTAL_FOV = 27.0
FRAME_W = 1920      # Pi 8MP camera at 1080p
CAM_OFFSET_PX = 40
PRINT_INTERVAL = 5.0

SENSOR_RANGES = {
    1: (0, 9),
    2: (9, 18),
    3: (18, 27),
}

SENSOR_LABELS = {
    1: "left",
    2: "center",
    3: "right",
}

#Helper func
def pixel_to_deg(px):
    return (px / FRAME_W) * TOTAL_FOV

def sensor_sees_object(sensor_num, obj_deg_min, obj_deg_max):
    s_min, s_max = SENSOR_RANGES[sensor_num]
    return obj_deg_min < s_max and obj_deg_max > s_min

def drain_queue(tof_queue: Queue, sd: dict):
    while not tof_queue.empty():
        try:
            msg = tof_queue.get_nowait()
            sd[msg["sensor_id"]] = msg["distance"]
        except Exception:
            break

if __name__ == "__main__":
    tof_queue = Queue()

    workers = []
    for sid in SENSOR_IDS:
        p = Process(target=tof, args=(tof_queue, sid), daemon=True)
        p.start()
        workers.append(p)

    last_print_time = time.time()

    print("Starting main loop...")

    while True:
        DO, OCT, OCB = getObjInfoNoCam()

        if not DO:
            sd = {sid: getSensorDistanceTof(sid) for sid in SENSOR_IDS}
            drain_queue(tof_queue, sd)

            wall_detected = any(sd[sid] <= MSR for sid in SENSOR_IDS)
            if wall_detected:
                print("No object detected — wall detected by sensor.")
            else:
                print("No object detected.")
            continue

        adj_OCT_x = OCT[0] + CAM_OFFSET_PX
        adj_OCB_x = OCB[0] + CAM_OFFSET_PX  # right edge of bounding box

        obj_deg_min = pixel_to_deg(adj_OCT_x)
        obj_deg_max = pixel_to_deg(adj_OCB_x)

        sd = {sid: getSensorDistanceTof(sid) for sid in SENSOR_IDS}
        drain_queue(tof_queue, sd)

        current_time = time.time()
        if current_time - last_print_time >= PRINT_INTERVAL:
            detected = False

            for sid in SENSOR_IDS:
                if sensor_sees_object(sid, obj_deg_min, obj_deg_max) and sd[sid] <= MSR:
                    print(f"Object to the {SENSOR_LABELS[sid]} at {sd[sid]:.2f}m away")
                    detected = True

            if not detected:
                print("Distance measurement unavailable.")
    
            