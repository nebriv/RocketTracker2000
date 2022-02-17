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
import serial
from utils.xbox import XboxController
import inputs
from imutils.video import FPS
import subprocess
from utils.camera import WebcamVideoStream
import traceback


tracking_lost_max_frames = 30

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

    tracking_start = False

    mode = "auto"
    wc = False
    testing = False

    def __init__(self):
        try:
            self.joy = XboxController()
        except inputs.UnpluggedError as err:
            print("Game pad not detected!")
        atexit.register(self.exit_handler)
        print("Starting keyboard monitor")
        keyboard_monitor = Thread(target=self.keyboard_monitor, daemon=True)
        keyboard_monitor.start()

        print("Starting controller monitor")
        controller_monitor = Thread(target=self.controller_monitor, daemon=True)
        controller_monitor.start()

        print("Starting video input")
        if self.testing:
            self.wc = cv2.VideoCapture("test_videos/3.mp4")
        else:
            self.wc = WebcamVideoStream(src=WEBCAM).start()
        print("Waiting for things to initialize")
        time.sleep(2)
        self.video_tracker()
        self.wc.stop()

    def keyPress(self, key):
        key = str(key).replace("'", "")
        if key == 'q':
            self.exit = True
        if key == 'm':
            self.mode = "manual"
        if key == "a":
            self.mode = "auto"

        if key == 't':
            self.tracking_start = True

    def keyboard_monitor(self):
        with Listener(on_press=self.keyPress) as listener:
            listener.join()

    def controller_monitor(self):
        while not self.exit:
            self.joy_input = self.joy.read()
            if self.joy_input['start'] == 1:
                self.tracking_start = True
            if self.joy_input['a'] == 1:
                if self.testing:
                    self.testing = False
                else:
                    self.testing = True


    def exit_handler(self):
        print("Good bye.")
        time.sleep(2)
        cv2.destroyAllWindows()
        if self.wc:
            self.wc.stop()
        if self.controller:
            self.controller.camera_cancel()
            self.controller.camera_go_home()


    def video_tracker(self):
        if self.testing:
            print("TESTING MODE ENABLED!")
        else:
            print("TEST MODE IS NOT ENABLED")

        if self.joy.connected:
            print("Controller connected!")
        else:
            print("Controller not connected!")

        print("Creating Tracker instance")
        tracker = cv2.TrackerCSRT_create()

        print("Reading frame to setup Camera Controller")
        frame = self.wc.read()
        #
        width = int(frame.shape[1] * 25 / 100)
        height = int(frame.shape[0] * 25 / 100)
        #
        try:
            frame = cv2.resize(frame, (width, height))
            self.controller = controller(frame.shape[1], frame.shape[0], serial_port=COMM_PORT)
        except Exception as err:
            print(err)
            exit()

        print("Enabling autofocus")
        self.controller.camera_enable_autofocus()
        #
        print("Showing preview")
        fps = FPS().start()
        while not self.exit and not self.tracking_start:
            frame = self.wc.read()
            # frame = cv2.resize(frame, (width, height))
            if self.joy.connected:
                cv2.putText(frame, 'Press Start to Select Tracking Object', (int(frame.shape[0] / 2) + 100, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                cv2.putText(frame, 'Press T to Select Tracking Object', (int(frame.shape[0] / 2) + 100, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow('Preview', frame)
            if self.joy.connected:
                Thread(target=self.controller.move, args=(self.joy_input['x'], self.joy_input['y'], self.joy_input['z'],)).start()
            fps.update()
            if cv2.waitKey(1) & 0XFF == 27:
                break
        fps.stop()
        print(fps.fps())

        cv2.destroyAllWindows()
        frame = self.wc.read()
        frame = cv2.resize(frame, (width, height))
        bbox = cv2.selectROI(frame)
        ok = tracker.init(frame, bbox)
        cv2.destroyAllWindows()
        tracking_lost_frame_count = 0

        prev_frame_time = 0
        new_frame_time = 0
        frame_counter = 0

        try:
            while not self.exit:
                frame = self.wc.read()
                clean_frame = frame.copy()
                new_frame_time = time.time()
                fps = 1 / (new_frame_time - prev_frame_time)
                prev_frame_time = new_frame_time
                fps = str(int(fps))
                # cv2.putText(clean_frame, fps, (7, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (100, 255, 0), 3, cv2.LINE_AA)
                if self.mode == "auto":
                    frame = cv2.resize(frame, (width, height))
                    ok, bbox = tracker.update(frame)
                    if ok:
                        (x, y, w, h) = [int(v) for v in bbox]
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2, 1)
                        tracking_lost_frame_count = 0
                        try:
                            Thread(target=self.controller.follow, args=(bbox,)).start()
                        except Exception as err:
                            print("CAUGHT ERROR: %s" % err)
                    else:
                        cv2.putText(frame, '------ TRACKING LOST! ------', (int(frame.shape[0] / 2) + 100, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                        tracking_lost_frame_count += 1

                    if tracking_lost_frame_count > tracking_lost_max_frames:
                        print("Switching to manual mode, tracking lost for more than %s frames." % tracking_lost_max_frames)
                        self.mode = "manual"

                    if self.testing:
                        cv2.imshow("Tracking Frame", frame)
                    cv2.imshow("Clean Frame", clean_frame)
                    if cv2.waitKey(1) & 0XFF == 27:
                        break

                elif self.mode == "manual":
                    cv2.putText(frame, '------ MANUAL CONTROL ------', (int(frame.shape[0] / 2) + 100, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    if self.testing:
                        cv2.imshow("Tracking Frame", frame)
                    cv2.imshow("Clean Frame", frame)
                    self.controller.move(self.joy_input['x'], self.joy_input['y'], self.joy_input['z'])
                    if cv2.waitKey(1) & 0XFF == 27:
                        break

            cv2.destroyAllWindows()


        except KeyboardInterrupt:
            exit()
        except Exception as err:
            print("CAUGHT ERROR: %s" % err)
            traceback.print_exc()
            exit()


tracker = RocketTracker()
