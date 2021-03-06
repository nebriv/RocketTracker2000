import socket
import cv2
import sys
import numpy as np
import serial
from utils import PID



class controller:
    """
    PID controller for VISCA over IP camera
    """

    last_x = None
    last_y = None
    last_z = None
    last_f = None

    def __init__(self, width, height, ip_address=None, port=52381, serial_port=None, sample_time=0.03) -> None:
        """
        new controller instance
        :param width: width of input frame
        :type width: int
        :param height: height of input frame
        :type height: int
        :return:
        :rtype: None
        """


        #fix: needs to load parameters from file
        self.WIDTH = width
        self.HEIGHT = height
        self.conn_type = None
        if ip_address:
            self.ip_address = ip_address
            self.port_number = port
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
            self.connection.connect((self.ip_address, self.port_number))
            self.conn_type = "network"
        elif serial_port:
            self.connection = serial.Serial(serial_port)
            self.conn_type = "serial"
        else:
            raise ValueError("Missing IP address or serial port.")

        #target values in pixel coordinates
        self.target_x = int(width/2) #int(width/2)
        self.target_y = int(height/2) #int(height/2)
        self.target_z = 106 #int(width/12)
        P = .0001
        I = .01
        D = .1

        self.pid_x = PID.PID(P, I, D)
        self.pid_x.SetPoint = self.target_x
        self.pid_x.setSampleTime(sample_time)

        self.pid_y = PID.PID(P, I, D)
        self.pid_y.SetPoint = self.target_y
        self.pid_y.setSampleTime(sample_time)

        self.pid_z = PID.PID(P, I, D)

        #motor saturation for integral, stops summing if saturated
        self.x_unsaturated = True
        self.y_unsaturated = True
        self.z_unsaturated = True

        #running sum of the error (integral)
        self.x_error_sum = 0
        self.y_error_sum = 0
        self.z_error_sum = 0

        #history of the error (derivative)  length defined by self._length
        self.x_error_history = np.array([0,0])
        self.y_error_history = np.array([0,0])
        self.z_error_history = np.array([0,0])
        #self.h_error_history = np.array([0,0])


        #acceptable exponents to control proportion equation
        #exponents are used to adjust response of the proportional error
        self.shape_list = [0.6, 0.76, 1, 1.32, 1.96, 2.2, 3, 5, 7, 21, 81]

        #pan/tilt parameters initial values
        self.p_gain = 0.4 #contribution of p component to total error
        self.p_slope = 1.0 # slope of proportional error response
        self.p_shape = 1 # index of shape for proportional error
        self.i_gain = 0 #contribution of i component to total error
        self.d_gain = 0 #contribution of d component to total error
        self.d_noise_reduction = 1 
        self.m_smooth = 1.0
        self.length = 3 #history length

        # camera does not move unless error 
        # error is greater than threshold
        self.x_threshold = 0.07
        self.y_threshold = 0.07

        #zoom parameters initial values
        self.z_p_gain = 1
        self.z_p_slope = 1 
        self.z_p_shape = 2
        self.z_i_gain = 1
        self.z_d_gain = 1
        self.z_d_noise_reduction = 1
        self.z_m_smooth = 1
        self.z_length = 1
        self.z_threshold = 0
        self.f_threshold = 0


    def nothing(self, x):
        pass

    def set_ip(self, ip):
        """
        IP Setter
        :param ip: new ip address
        :type ip: String
        :return:
        :rtype: None
        """
        try:
            self.ip_address = ip
            self.connection.close()
            self.connection.connect((self.ip_address, self.port_number))
        except:
            print("Connection Error: Could not set camera ip address")
        
    def set_port(self, port):
        """
        Network Port Setter
        :param port: new port number
        :type port: String
        :return:
        :rtype: None
        """
        try:
            self.port_number = port
            self.connection.close()
            self.connection.connect((self.ip_address, self.port_number))
        except:
            print("Connection Error: Could not set camera port")


    def follow(self, box):
        x, y, w, h = box
        center_x = x + w/2
        center_y = y + h/2
        # print("Box Center X: %s - Box Center Y: %s" % (center_x, center_y))

        x_error = center_x - self.target_x
        y_error = center_y - self.target_y

        # print("X %s - Y %s" % (x_error, y_error))

        x_error = x_error * .001
        y_error = y_error * .001
        # print("X %s - Y %s" % (x_error, y_error))

        # build VISCA hex command
        command_type = '81010601'
        pan_speed = '00'
        tilt_speed = '00'
        pan_direction = '03'
        tilt_direction = '03ff'
        zoom_header = '81010407'
        zoom_speed = '00ff'

        # get magnitiude and direction in hex for x and y
        if x_error > self.x_threshold:
            pan_speed = str(int(x_error * 34)).zfill(2)
            pan_direction = '02'
        elif x_error < 0 - self.x_threshold:
            pan_speed = str(int(x_error * -34)).zfill(2)
            pan_direction = '01'

        if y_error > self.y_threshold:
            tilt_speed = str(int(y_error * 30)).zfill(2)
            tilt_direction = '02ff'
        elif y_error < 0 - self.y_threshold:
            tilt_speed = str(int(y_error * -30)).zfill(2)
            tilt_direction = '01ff'

        command = (command_type + pan_speed + tilt_speed + pan_direction + tilt_direction)
        self.send_command(command)

    def follow_pid(self, box):
        """
        Moves camera to follow a bounding box in the frame.
        :param box: tuple containing box upper left corner x, y, width, and height
        :return:
        :rtype: None
        """

        #calculate difference between target and bounding box
        x, y, w, h = box
        center_x = x + w/2
        center_y = y + h/2
        # print("Box Center X: %s - Box Center Y: %s" % (center_x, center_y))

        x_error = center_x - self.target_x
        y_error = center_y - self.target_y
        # z_error = w - self.target_z
        z_error = 0
        # print("Raw x_error: %s - Raw y_error: %s - Raw z_error: %s" % (x_error, y_error, z_error))
        
        # #calculate PID error
        # px, py, pz = self.calculate_p(x_error, y_error, z_error)
        # ix, iy, iz = self.calculate_i(x_error, y_error, z_error)
        # dy, dx, dz = self.calculate_d(x_error, y_error, z_error)
        # print("Calculated PX: %s" % px)
        #
        # #adjust for gain. Assumes gains add up to 1
        # px *= self.p_gain
        # py *= self.p_gain
        # pz *= self.z_p_gain
        #
        # ix *= self.i_gain
        # iy *= self.i_gain
        # iz *= self.z_i_gain
        #
        # dy *= self.d_gain
        # dx *= self.d_gain
        # dz *= self.z_d_gain
        #
        # x_pid_error = px + ix + dx
        # y_pid_error = py + iy + dy
        # z_pid_error = pz + iz + dz
        # self.move(x_pid_error, y_pid_error, z_pid_error)
        self.pid_x.update(x_error)
        self.pid_y.update(y_error)

        # print("X PID OUTPUT: %s" % self.pid_x.output)
        # print("Y PID OUTPUT: %s" % self.pid_y.output)

        self.move(self.pid_x.output, self.pid_y.output, 0)

    def camera_go_home(self):
        self.send_command('81010604FF')

    def camera_cancel(self):
        self.send_command('81010001FF')

    def camera_reset(self):
        self.send_command('81010605FF')

    def camera_enable_autofocus(self):
        self.send_command('8101043802FF')

    def camera_recall_preset(self, preset):
        print(f'{preset:x}')
        print(f'8101043F020{preset:x}FF')
        # self.send_command(f'8101043F020{preset:x}FF')

    def camera_manual_focus(self):
        self.send_command('8101043803FF')

    def move(self, x_error, y_error, z_error, focus=0):
        """
        Generates VISCA commands to move PTZOptics Camera
        :param x_error: magnitude of movement on the x plain clamped between -1 and 1
        :param y_error: magnitude of movement on the y plain clamped between -1 and 1
        :param z_error: magnitude of zoom clamped between -1 and 1
        :return:
        :rtype: None
        """
        #clamp error to -1 and 1 and alert of motor saturation for integral
        if abs(x_error) > 1:
            self.x_unsaturated = False
            x_error = min(1, max(-1, x_error))
        else:
            self.x_unsaturated = True

        if abs(y_error) > 1:
            self.y_unsaturated = False
            y_error = min(1, max(-1, y_error))
        else:
            self.y_unsaturated = True

        if abs(z_error) > 1:
            self.z_unsaturated = False
            z_error = min(1, max(-1, z_error))
        else:
            self.z_unsaturated = True
        
        # print("X Error: %s - Y Error: %s - Z Error: %s" % (x_error, y_error, z_error))

        if not self.x_unsaturated or not self.y_unsaturated:
            print("SATURATION WAAARRRRNIIINNGGGG!!!!!!!!! X: %s Y: %s Z: %s" % (self.x_unsaturated, self.y_unsaturated, self.z_unsaturated))

        #build VISCA hex command
        command_type = '81010601'
        pan_speed = '00'
        tilt_speed = '00'
        pan_direction = '03'
        tilt_direction = '03ff'
        zoom_header = '81010407'
        zoom_speed = '00ff'

        #get magnitiude and direction in hex for x and y
        if x_error > self.x_threshold:
            pan_speed = str(int(x_error * 24)).zfill(2)
            pan_direction = '02'
        elif x_error < 0 - self.x_threshold:
            pan_speed = str(int(x_error * -24)).zfill(2)
            pan_direction = '01'

        if y_error > self.y_threshold:
            tilt_speed = str(int(y_error * 20)).zfill(2)
            tilt_direction = '02ff'
        elif y_error < 0 - self.y_threshold:
            tilt_speed = str(int(y_error * -20)).zfill(2)
            tilt_direction = '01ff'

        command = (command_type + pan_speed + tilt_speed + pan_direction + tilt_direction)
        if command != self.last_x:
            self.send_command(command)
            self.last_x = command

        #get magnitude and direction in hex for zoom
        if z_error > self.z_threshold:
            zoom_speed = '2{}ff'.format(str(int(z_error * 7)))
        elif z_error < 0 - self.z_threshold:
            zoom_speed = '3{}ff'.format(str(int(z_error * -7)))
        zoom_command = zoom_header + zoom_speed

        if zoom_command != self.last_z:
            self.send_command(zoom_command)
            self.last_z = zoom_command

        focus_speed = 0
        if focus > self.f_threshold:
            focus_speed = int(focus * 7)
        elif focus < 0 - self.f_threshold:
            focus_speed = int(focus * 7)


        code = '81010408'
        speed_hex = f'{abs(focus_speed):x}'

        if focus_speed == 0:
            direction_hex = '0'
        elif focus_speed > 0:
            direction_hex = '2'
        else:
            direction_hex = '3'

        focus_command = code + direction_hex + speed_hex + "FF"
        if focus_command != self.last_f:
            self.send_command(focus_command)
            self.last_f = focus_command

    def send_command(self, command):
        """
        Sends VISCA hex command to camera
        :param command: hex code to send to camera
        :type command: String
        :return:
        :rtype: None
        """
        # print("Sending command: %s" % command)
        try:
            data = bytes.fromhex(command)
            if self.conn_type == "network":
                self.connection.send(data)
            elif self.conn_type == "serial":
                self.connection.write(data)
            
        except:
            print("Connection Error: Could not send VISCA command %s to camera" % command)

    def calculate_p(self, x_error, y_error, z_error):
        """
        Calculates proportional error.
        :param x_error: absolute difference between target x and 
        bounding box center between -1 and 1
        :param y_error: absolute difference between target y and 
        bounding box center between -1 and 1
        :param z_error: absolute difference between target width 
        and bounding box width between -1 and 1
        :return: proportional error for x, y, and zoom between -1 and 1
        """
        #proportional error calculated as slope/10 x^shape
        #error is clamped between 1 and -1
        # print(self.p_slope / 10)
        # print(x_error)
        # print(x_error**self.shape_list[self.p_shape])
        # print("DEBUG: %s" % (self.p_slope/10) * x_error**self.shape_list[self.p_shape])
        px = max(-1.0, min(1.0, (self.p_slope/10) * x_error**self.shape_list[self.p_shape]))
        py = max(-1.0, min(1.0, (self.p_slope/10) * y_error**self.shape_list[self.p_shape]))
        pz = max(-1.0, min(1.0, (self.z_p_slope/10) * z_error**self.shape_list[self.z_p_shape]))
        



        return px, py, pz
       
            
    def calculate_i(self, x_error, y_error, z_error):
        """
        Calculates integral error by keeping a running error sum 
        when not saturated.
        :param x_error: absolute difference between target x and 
        bounding box center between -1 and 1
        :param y_error: absolute difference between target y and 
        bounding box center between -1 and 1
        :param z_error: absolute difference between target width 
        and bounding box width between -1 and 1
        :return: integral error
        """
        # does not accumulate if motor is saturated (at max speed)
        self.x_error_sum += x_error * self.x_unsaturated
        self.y_error_sum += y_error * self.y_unsaturated
        self.z_error_sum += z_error * self.z_unsaturated

        return self.x_error_sum, self.y_error_sum, self.z_error_sum

    def calculate_d(self, x_error, y_error, z_error):
        """
        Approximates derivative of the error from history.
        :param x_error: absolute difference between target x and 
        bounding box center between -1 and 1
        :param y_error: absolute difference between target y and 
        bounding box center between -1 and 1
        :param z_error: absolute difference between target width 
        and bounding box width between -1 and 1
        :return: derivative error for x, y, and zoom between -1 and 1
        """
        #maintain history length
        self.x_error_history = self.x_error_history[
            max(0, self.x_error_history.size - self.length):self.x_error_history.size]
        self.y_error_history = self.y_error_history[
            max(0, self.y_error_history.size - self.length):self.y_error_history.size]
        self.z_error_history = self.z_error_history[
            max(0, self.z_error_history.size - self.z_length):self.z_error_history.size]
        

        #add new error
        self.x_error_history = np.append(self.x_error_history, x_error)
        self.y_error_history = np.append(self.y_error_history, y_error)
        self.z_error_history = np.append(self.z_error_history, z_error)
        

        #calculate derivative with respect to time
        dx = np.mean(np.diff(self.x_error_history))
        dy = np.mean(np.diff(self.y_error_history))
        dz = np.mean(np.diff(self.z_error_history))
        

        return dx, dy, dz
        