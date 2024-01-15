from gpiozero import MotionSensor, DistanceSensor, OutputDevice, Device
from gpiozero.pins.pigpio import PiGPIOFactory
from rpi_lcd import LCD

pir = MotionSensor(19)

if __name__ == "__main__":
   try:
        while True:
            pir.wait_for_motion()
            print("You moved")
            pir.wait_for_no_motion()
   except KeyboardInterrupt:
       pass