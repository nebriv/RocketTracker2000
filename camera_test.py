import time
from visca_over_ip import Camera

cam = Camera('192.168.0.123')  # Your camera's IP address or hostname here

cam.pantilt_home()

while True:
    cam.pantilt(pan_speed=1, pan_position=5, relative=True, tilt_speed=0)
    time.sleep(1)  # wait one second
    cam.pantilt(pan_speed=-1, pan_position=5, relative=True, tilt_speed=0)