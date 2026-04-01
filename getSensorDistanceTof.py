import time
import board # type: ignore
import busio # type: ignore
import adafruit_vl53l0x # type: ignore
from gpiozero import OutputDevice

xshut1 = OutputDevice(4, initial_value=False)
xshut2 = OutputDevice(5, initial_value=False)
xshut3 = OutputDevice(6, initial_value=False)

i2c = busio.I2C(board.SCL, board.SDA)

xshut1.on(); time.sleep(0.1)
vl531 = adafruit_vl53l0x.VL53L0X(i2c); vl531.set_address(0x27)

xshut2.on(); time.sleep(0.1)
vl532 = adafruit_vl53l0x.VL53L0X(i2c); vl532.set_address(0x28)

xshut3.on(); time.sleep(0.1)
vl533 = adafruit_vl53l0x.VL53L0X(i2c)

_SENSORS = {1: vl531, 2: vl532, 3: vl533}

def getSensorDistanceTof(sensor_num: int) -> float:
    sensor = _SENSORS.get(sensor_num)
    if sensor is None:
        raise ValueError(f"sensor_num must be 1, 2, or 3 — got {sensor_num}")
    try:
        mm = sensor.range
        return float("inf") if mm <= 0 else mm / 1000.0
    except Exception as e:
        print(f"[getSensorDistanceTof] sensor {sensor_num} error: {e}")
        return float("inf")