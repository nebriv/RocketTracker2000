# importing the required libraries
import cv2
import numpy as np
from threading import Thread
import itertools as it
import ctypes
from queue import Queue
from utils.VISCA_controller import controller
import time
from utils.utils import DominantColors
import atexit
from pynput.keyboard import Key, Listener

WEBCAM = 1

COMM_PORT = "COM3"
# OR IP
IP_ADDRESS = "192.168.1.191"
PORT = 52381

user32 = ctypes.windll.user32
screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


class RocketTracker:
    last_x = None
    last_y = None

    x_changes = Queue()
    y_changes = Queue()

    exit = False
    controller = False

    def __init__(self):
        atexit.register(self.exit_handler)
        keyboard_monitor = Thread(target=self.keyboard_monitor)
        keyboard_monitor.start()
        video_tracker = Thread(target=self.video_tracker)
        video_tracker.start()


    def keyPress(self, key):
        if key == 'q':
            print(key)


    def keyboard_monitor(self):
        with Listener(on_press=self.keyPress) as listener:
            listener.join()


    def exit_handler(self):
        print("Good bye.")
        if self.controller:
            self.controller.camera_cancel()
            self.controller.camera_go_home()

    def video_tracker(self):
        tracker = cv2.TrackerCSRT_create()
        video = cv2.VideoCapture(WEBCAM)
        ret, frame = video.read()
        # dc = DominantColors(frame, clusters=1)
        # colors = dc.dominantColors()


        print("Waiting for blue screen to clear.")
        time.sleep(15)
        # while self.exit == False:
        #     print("Hey")
        #     print(self.exit)
        #     time.sleep(1)


        # if frame.shape[0]+500 > screensize[0]:
        #     print("RESIZING")
        #     print()
        #     frame = cv2.resize(frame, (int(round(frame.shape[1]/1.7, 0)), int(round(frame.shape[0]/1.7, 0))))



        # frame = cv2.resize(frame, (1660, 1240))
        bbox = cv2.selectROI(frame)
        ok = tracker.init(frame, bbox)

        self.controller = controller(frame.shape[1], frame.shape[0], serial_port=COMM_PORT)

        while not self.exit:
            ok, frame = video.read()
            # if frame.shape[0]+500 > screensize[0]:
            #     frame = cv2.resize(frame, (int(round(frame.shape[1]/1.7, 0)), int(round(frame.shape[0]/1.7, 0))))
            # frame = cv2.resize(frame, (1660, 1240))
            if not ok:
                break
            ok, bbox = tracker.update(frame)
            if ok:
                (x, y, w, h) = [int(v) for v in bbox]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2, 1)

                try:
                    self.controller.follow(bbox)
                except Exception as err:
                    print("CAUGHT ERROR: %s" % err)

            else:
                cv2.putText(frame, 'Error', (100, 0), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow('Tracking', frame)
            if cv2.waitKey(1) & 0XFF == 27:
                break
        cv2.destroyAllWindows()



tracker = RocketTracker()
