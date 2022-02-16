# importing the required libraries
import cv2
import numpy as np
from threading import Thread
import itertools as it
import ctypes
from queue import Queue
from simple_pid import PID
from utils.VISCA_controller import controller
import time
from visca_over_ip import Camera

WEBCAM = 1

COMM_PORT = "COM3"
# OR IP
IP_ADDRESS = "192.168.1.191"
PORT = 52381


user32 = ctypes.windll.user32
screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


from collections import deque
import itertools as it

def moving_average(iterator, length, step=1):
    window = deque(it.islice(iterator, 0, length*step, step))
    total = sum(window)
    yield total / length
    for i in it.islice(iterator, length*step, None, step):
        total -= window.popleft()
        total += i
        window.append(i)
        yield total / length


class RocketTracker:
    last_x = None
    last_y = None

    x_changes = Queue()
    y_changes = Queue()

    def __init__(self):

        video_tracker = Thread(target=self.video_tracker)
        video_tracker.start()

    def video_tracker(self):
        tracker = cv2.TrackerCSRT_create()
        video = cv2.VideoCapture(WEBCAM)



        x_pid = PID(1, 0.1, 0.05, setpoint=0)
        x_pid.sample_time = 1 / round(video.get(cv2.CAP_PROP_FPS))

        y_pid = PID(1, 0.1, 0.05, setpoint=0)
        y_pid.sample_time = 1 / round(video.get(cv2.CAP_PROP_FPS))

        ret, frame = video.read()



        if frame.shape[0]+500 > screensize[0]:
            print("RESIZING")
            print()
            frame = cv2.resize(frame, (int(round(frame.shape[1]/1.7, 0)), int(round(frame.shape[0]/1.7, 0))))

        self.controller = controller(frame.shape[1], frame.shape[0], serial_port=COMM_PORT)


        # frame = cv2.resize(frame, (1660, 1240))
        bbox = cv2.selectROI(frame)
        ok = tracker.init(frame, bbox)
        while True:
            ok, frame = video.read()
            if frame.shape[0]+500 > screensize[0]:
                frame = cv2.resize(frame, (int(round(frame.shape[1]/1.7, 0)), int(round(frame.shape[0]/1.7, 0))))
            # frame = cv2.resize(frame, (1660, 1240))
            if not ok:
                break
            ok, bbox = tracker.update(frame)
            if ok:
                (x, y, w, h) = [int(v) for v in bbox]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2, 1)
                c_x, c_y = self.get_center(x, y, w, h)
                cv2.circle(frame, (c_x, c_y), 1, (0, 0, 255), 5)

                # Get X Distance from Center
                self.controller.follow(bbox)

            else:
                cv2.putText(frame, 'Error', (100, 0), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow('Tracking', frame)
            if cv2.waitKey(1) & 0XFF == 27:
                break
        cv2.destroyAllWindows()



tracker = RocketTracker()
