Heavily borrowed from:

https://github.com/bendostie/PTZ_PID


https://github.com/Mjrovai/OpenCV-Object-Face-Tracking

https://github.com/josephdadams/udp-to-serial

https://pypi.org/project/simple-pid/


https://visca-over-ip.readthedocs.io/en/latest/camera.html

https://github.com/misterhay/VISCA-IP-Controller/blob/main/visca_over_ip/camera.py

https://github.com/Sciguymjm/python-visca/blob/master/visca/camera.py


https://pythonwife.com/object-tracking-in-opencv/

https://gist.github.com/bajcmartinez/67a47d616e1805b81e54f4724358b8fe

https://stackoverflow.com/a/66867816


Notes

https://www.guidodiepen.nl/2017/02/detecting-and-tracking-a-face-with-python-and-opencv/

# Start up

1. Connect XBox Controller
2. Start Docker
3. docker run -d -p 1935:1935 --name nginx-rtmp tiangolo/nginx-rtmp
4. Start SplitCam
5. Confirm splitcam sending to rtmp://127.0.0.1/live/ptz
6. Confirm OBS has above RTMP as media source
7. CD to tracker dir
8. venv\Scripts\activate
9. python main.py
10. Zoom in and focus on target
11. Hit start on the controller.
12. Select target and hit enter
13. Sit back and relax
14. ???
15. Profit
