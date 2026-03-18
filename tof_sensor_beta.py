import time
import board
import busio
import adafruit_vl53l0x
from gpiozero import LED

# Your original LED setup
red = LED(24)    # pin 18
yellow = LED(27) # pin 13
blue = LED(22)   # pin 15
green = LED(23)  # pin 16

# Initialize I2C and sensor
i2c = busio.I2C(board.SCL, board.SDA)
vl53 = adafruit_vl53l0x.VL53L0X(i2c)

def set_leds(r, y, b, g):
    for led, state in zip([red, yellow, blue, green], [r, y, b, g]):
        if state:
            led.on()
        else:
            led.off()

while True:
    distance_mm = vl53.range
    distance_m = distance_mm / 1000.0
    print(f"Range: {distance_m:.2f}m")
    
    if distance_m < 0.2:
        set_leds(1, 0, 0, 0)  # red
    elif distance_m < 0.5:
        set_leds(0, 1, 0, 0)  # yellow
    elif distance_m < 1:
        set_leds(0, 0, 1, 0)  # blue
    else:
        set_leds(0, 0, 0, 1)  # green
    
    time.sleep(1.0)