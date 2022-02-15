import time
from visca_over_ip import Camera

cam = Camera('192.168.0.123')  # Your camera's IP address or hostname here

while True:
    cam.pantilt(pan_speed=-12, tilt_speed=0)
    time.sleep(1)  # wait one second
    cam.pantilt(pan_speed=12, tilt_speed=0)