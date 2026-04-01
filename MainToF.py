from getObjInfoNoCam import getObjInfoNoCam
from getSensorDistanceNoTof import getSensorDistanceNoTof
import math
import time

VL = [1, 2, 3]
MSR = 2.0        # Max Sensor Range (meters)
TOTAL_FOV = 27.0
FRAME_W = 1920   # Pi 8MP camera at 1080p
CAM_OFFSET_PX = 40

SENSOR_RANGES = {
    1: (0, 9),
    2: (9, 18),
    3: (18, 27),
}

last_print_time = time.time()
PRINT_INTERVAL = 5.0

def pixel_to_deg(px):
    return (px / FRAME_W) * TOTAL_FOV

def sensor_sees_object(sensor_num, obj_deg_min, obj_deg_max):
    s_min, s_max = SENSOR_RANGES[sensor_num]
    return obj_deg_min < s_max and obj_deg_max > s_min

while True:
    DO, OCT, OCB = getObjInfoNoCam()

    if not DO:
        print("No object detected.")
        break

    adj_OCT = (OCT[0], OCT[1] + CAM_OFFSET_PX)
    adj_OCB = (OCB[0], OCB[1] + CAM_OFFSET_PX)

    obj_deg_min = pixel_to_deg(adj_OCT[0])
    obj_deg_max = pixel_to_deg(adj_OCB[0])
# right edge of bounding box

    current_time = time.time()
    if current_time - last_print_time >= PRINT_INTERVAL:
        SD = {i: getSensorDistanceNoTof(i) for i in VL}

        labels = {1: "left", 2: "center", 3: "right"}
        detected = False

        for i in VL:
            if sensor_sees_object(i, obj_deg_min, obj_deg_max) and SD[i] <= MSR:
                print(f"Object to the {labels[i]} at {SD[i]}m away")
                detected = True

        if not detected:
            print("Distance measurement unavailable.")

        last_print_time = current_time