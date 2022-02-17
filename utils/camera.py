import cv2
from threading import Thread
import time
#

class WebcamVideoStream(object):
    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        # FPS = 1/X
        # X = desired FPS
        self.FPS = 1/30
        self.FPS_MS = int(self.FPS * 1000)
        (self.grabbed, self.frame) = self.stream.read()
        self.stopped = False
        # Start frame retrieval thread


    def start(self):
        # start the thread to read frames from the video stream
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()
        return self

    def update(self):
        while not self.stopped:
            if self.stream.isOpened():
                (self.status, self.frame) = self.stream.read()
            time.sleep(self.FPS)

    def show_frame(self):
        cv2.imshow('frame', self.frame)
        cv2.waitKey(self.FPS_MS)

    def read(self):
        # return the frame most recently read
        return self.frame

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True

# class WebcamVideoStream:
#     def __init__(self, src=0):
#         # initialize the video camera stream and read the first frame
#         # from the stream
#
#
#         self.stream = cv2.VideoCapture(src + cv2.CAP_DSHOW)
#         codec = 0x47504A4D  # MJPG
#         self.stream.set(cv2.CAP_PROP_FPS, 60.0)
#         self.stream.set(cv2.CAP_PROP_FOURCC, codec)
#         # self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
#
#         # self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
#         self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
#         self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 1280)
#         # self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
#         # self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
#         # self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('m', 'j', 'p', 'g'))
#         (self.grabbed, self.frame) = self.stream.read()
#         # initialize the variable used to indicate if the thread should
#         # be stopped
#         self.stopped = False
#
#     def start(self):
#         # start the thread to read frames from the video stream
#         Thread(target=self.update, args=()).start()
#         return self
#
#     def update(self):
#         # keep looping infinitely until the thread is stopped
#         while True:
#             # if the thread indicator variable is set, stop the thread
#             if self.stopped:
#                 return
#             # otherwise, read the next frame from the stream
#             (self.grabbed, self.frame) = self.stream.read()
#
#     def read(self):
#         # return the frame most recently read
#         return self.frame
#
#     def stop(self):
#         # indicate that the thread should be stopped
#         self.stopped = True