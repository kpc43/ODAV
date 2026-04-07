from getObjInfoNoCam import getObjInfoNoCam
from getSensorDistanceNoTof import getSensorDistanceNoTof
from queue import Queue
import math
import time
import threading

VL = [1, 2, 3]
MSR = 2.0        # Max Sensor Range (meters)
TOTAL_FOV = 27.0
FRAME_W = 1920   # Pi 8MP camera at 1080p
CAM_OFFSET_PX = 40  # camera is ~1 inch above sensors, tune as needed
POLL_INTERVAL = 0.5

SENSOR_RANGES = {
    1: (0, 9),
    2: (9, 18),
    3: (18, 27),
}

last_print_time = time.time()
PRINT_INTERVAL = 1.0

def pixel_to_deg(px):
    return (px / FRAME_W) * TOTAL_FOV

def sensor_sees_object(sensor_num, obj_deg_min, obj_deg_max):
    s_min, s_max = SENSOR_RANGES[sensor_num]
    return obj_deg_min < s_max and obj_deg_max > s_min

def tof(tof_queue: Queue, sensor_id: int):
    # Message format: {"sensor_id": int, "distance": float}
    
    while True:
        distance = getSensorDistanceNoTof(sensor_id)
        tof_queue.put({
            "sensor_id": sensor_id,
            "distance": distance
        })
        time.sleep(POLL_INTERVAL)

# Create queue and start TOF threads
tof_queue = Queue()
threads = []

for sensor_id in VL:
    t = threading.Thread(target=tof, args=(tof_queue, sensor_id), daemon=True)
    t.start()
    threads.append(t)

print("TOF sensors running. Starting main loop...\n")

# Main loop - reads from queue instead of calling getSensorDistanceNoTof directly
while True:
    DO, OCT, OCB = getObjInfoNoCam()

    if not DO:
        print("No object detected.")
        break

    # shift bounding box down to account for camera being above sensors
    adj_OCT = (OCT[0], OCT[1] + CAM_OFFSET_PX)
    adj_OCB = (OCB[0], OCB[1] + CAM_OFFSET_PX)

    obj_deg_min = pixel_to_deg(adj_OCT[0])
    obj_deg_max = pixel_to_deg(adj_OCB[0])

    current_time = time.time()
    if current_time - last_print_time >= PRINT_INTERVAL:
        # Get latest readings from queue for all sensors
        SD = {}
        
        # Non-blocking queue reads - get all available data
        while not tof_queue.empty():
            msg = tof_queue.get()
            SD[msg["sensor_id"]] = msg["distance"]
        
        # If any sensor missing, use previous values or fetch directly
        for sensor_id in VL:
            if sensor_id not in SD:
                SD[sensor_id] = getSensorDistanceNoTof(sensor_id)

        labels = {1: "left", 2: "center", 3: "right"}
        detected = False

        for i in VL:
            if SD[i] <= MSR:
                print(f"Object to the {labels[i]} at {SD[i]}m away")
                detected = True

        if not detected:
            print("Distance measurement unavailable.")

        last_print_time = current_time

    # Small delay to prevent CPU spinning
    time.sleep(0.1)