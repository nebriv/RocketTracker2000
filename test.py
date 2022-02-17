from utils.camera import WebcamVideoStream
import cv2
from imutils.video import FPS

fps = FPS()
fps.start()
wc = WebcamVideoStream(src=0).start()
frames = 0
while frames < 700:
    frame = wc.read()
    cv2.imshow('frame', frame)
    fps.update()
    if cv2.waitKey(1) & 0XFF == 27:
        break
    frames += 1

fps.stop()
print(fps.fps())