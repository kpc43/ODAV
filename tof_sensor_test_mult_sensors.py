import time
import board # type: ignore
import busio # type: ignore
import adafruit_vl53l0x # type: ignore
from gpiozero import OutputDevice

xshut1 = OutputDevice(4, initial_value=False)
xshut2 = OutputDevice(5, initial_value=False)
xshut3 = OutputDevice(6, initial_value=False)

i2c = busio.I2C(board.SCL, board.SDA)

xshut1.on()
time.sleep(0.1)
vl531 = adafruit_vl53l0x.VL53L0X(i2c)
vl531.set_address(0x27)

xshut2.on()
time.sleep(0.1)
vl532 = adafruit_vl53l0x.VL53L0X(i2c)
vl532.set_address(0x28)

xshut3.on()
time.sleep(0.1)
vl533 = adafruit_vl53l0x.VL53L0X(i2c)



while True:
    print(f"Sensor1: {vl531.range:.2f}mm")
    print(f"Sensor2: {vl532.range:.2f}mm")
    print(f"Sensor3: {vl533.range:.2f}mm")

    time.sleep(1.0)
