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

testing = False
tracking_lost_max_frames = 30

WEBCAM = 1

COMM_PORT = "COM3"
# OR IP
IP_ADDRESS = "192.168.1.191"
PORT = 52381

user32 = ctypes.windll.user32
screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


class WebcamVideoStream:
    def __init__(self, src=0):
        # initialize the video camera stream and read the first frame
        # from the stream
        self.stream = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        (self.grabbed, self.frame) = self.stream.read()
        # initialize the variable used to indicate if the thread should
        # be stopped
        self.stopped = False

    def start(self):
        # start the thread to read frames from the video stream
        Thread(target=self.update, args=()).start()
        return self

    def update(self):
        # keep looping infinitely until the thread is stopped
        while True:
            # if the thread indicator variable is set, stop the thread
            if self.stopped:
                return
            # otherwise, read the next frame from the stream
            (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        # return the frame most recently read
        return self.frame

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True


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

    def __init__(self):
        try:
            self.joy = XboxController()
        except inputs.UnpluggedError as err:
            print("Game pad not detected!")
        atexit.register(self.exit_handler)
        keyboard_monitor = Thread(target=self.keyboard_monitor, daemon=True)
        keyboard_monitor.start()
        video_tracker = Thread(target=self.video_tracker, daemon=True)
        video_tracker.start()
        video_tracker.join()

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
        if testing:
            print("TESTING MODE ENABLED!")
        else:
            print("TEST MODE IS NOT ENABLED")

        tracker = cv2.TrackerCSRT_create()
        if testing:
            self.video = cv2.VideoCapture("test_videos/3.mp4")
        else:
            # self.video = cv2.VideoCapture(WEBCAM)
            self.wc = WebcamVideoStream(src=WEBCAM).start()
            # self.video.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            # self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            # print(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))

        frame = self.wc.read()
        # if not frame:
        #     print("Unable to get video feed")
        #     exit()
        try:
            self.controller = controller(frame.shape[1], frame.shape[0], serial_port=COMM_PORT)
        except Exception as err:
            print(err)
            exit()
        self.controller.camera_enable_autofocus()

        dc = DominantColors(frame, 1)
        colors = dc.dominantColors()

        if not testing:
            print("Waiting for blue screen to clear.")
            print(colors)
            while not self.exit and colors[0][2] > 199:
                print(colors)
                frame = self.wc.read()
                dc = DominantColors(frame, 1)
                colors = dc.dominantColors()

        # while not self.exit and not self.tracking_start:
        #     ret, frame = self.video.read()
        #     cv2.imshow('Press T to select object', frame)
        #     if cv2.waitKey(1) & 0XFF == 27:
        #         break

        frame = self.wc.read()

        bbox = cv2.selectROI(frame)
        ok = tracker.init(frame, bbox)
        cv2.destroyAllWindows()
        tracking_lost_frame_count = 0


        fps = FPS().start()

        try:
            while not self.exit:
                if self.mode == "auto":
                    frame = self.wc.read()

                    #
                    # # ok, frame = video.read()
                    clean_frame = frame.copy()
                    # if frame.shape[0]+500 > screensize[0]:
                    #     frame = cv2.resize(frame, (int(round(frame.shape[1]/1.7, 0)), int(round(frame.shape[0]/1.7, 0))))
                    # frame = cv2.resize(frame, (1660, 1240))
                    ok, bbox = tracker.update(frame)
                    if ok:
                        (x, y, w, h) = [int(v) for v in bbox]
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2, 1)
                        tracking_lost_frame_count = 0
                        try:
                            # self.controller.follow(bbox)
                            pass
                        except Exception as err:
                            print("CAUGHT ERROR: %s" % err)

                    else:
                        cv2.putText(frame, '------ TRACKING LOST! ------', (int(frame.shape[0] / 2) + 100, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                        tracking_lost_frame_count += 1

                    if tracking_lost_frame_count > tracking_lost_max_frames:
                        self.mode = "manual"
                    frame = cv2.resize(frame,
                                       (int(round(frame.shape[1] / 2.5, 0)), int(round(frame.shape[0] / 2.5, 0))))
                    cv2.imshow('Tracking', frame)
                    cv2.imshow("Clean Frame", clean_frame)
                    if cv2.waitKey(1) & 0XFF == 27:
                        break
                    fps.update()

                elif self.mode == "manual":
                    cv2.putText(frame, '------ MANUAL CONTROL ------', (int(frame.shape[0] / 2) + 100, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    frame = self.Q.get()
                    cv2.imshow('Tracking', frame)
                    print(self.joy.read())
                    x, y = self.joy.read()
                    self.controller.move(x, y, 0)
                    if cv2.waitKey(1) & 0XFF == 27:
                        break
                    fps.update()

            cv2.destroyAllWindows()
            fps.stop()


        except KeyboardInterrupt:
            exit()
        except Exception as err:
            print(err)
            exit()


tracker = RocketTracker()
