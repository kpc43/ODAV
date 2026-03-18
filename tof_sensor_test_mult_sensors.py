import time
import board
import busio
import adafruit_vl53l0x
from gpiozero import OutputDevice

xshut1 = OutputDevice(17, initial_value=False)
xshut2 = OutputDevice(27, initial_value=False)


i2c = busio.I2C(board.SCL, board.SDA)

xshut1.on()
time.sleep(0.1)
vl531 = adafruit_vl53l0x.VL53L0X(i2c)
vl531.set_address(0x30)

xshut2.on()
time.sleep(0.1)
vl532 = adafruit_vl53l0x.VL53L0X(i2c)




while True:
    print(f"Sensor1: {vl531.range:.2f}mm")
    print(f"Sensor2: {vl532.range:.2f}mm")

    time.sleep(1.0)