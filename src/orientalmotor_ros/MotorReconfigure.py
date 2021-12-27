#!/usr/bin/env python

import rospy

from dynamic_reconfigure.server import Server
from orientalmotor_ros.cfg import motorConfig
from orientalmotor_ros.msg import motor
from rospy import client
import serial
import time
import Tkinter as tk
import struct

class modbus_ros():
    def __init__(self):
        self.client = serial.Serial("/dev/ttyUSB0", 115200, timeout=0.01, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE)
        self.size = 16
        self.pulse_angle= 0.36
        print(self.client.name)
        self.srv = Server(motorConfig, self.callback)
        self.master = tk.Tk()
        button1 = tk.Button(self.master, text="positiong rotate", command=lambda: self.positioning_rotate(motor))
        button1.pack()
        button2 = tk.Button(self.master, text="continuous rotate", command=lambda: self.continuous_rotate(motor))
        button2.pack()
        button3 = tk.Button(self.master, text="stop rotate", command=lambda:self._off())
        button3.pack()
        self.master.mainloop()

    def callback(self, config, level):
        rospy.loginfo("""Reconfigure Request: {rpm}, {angle}, {reverse}""".format(**config))
        motor.rpm = config['rpm']
        motor.angle = config['angle']
        motor.reverse = config['reverse']
        motor.acceleration = config['acceleration']
        motor.deceleration = config['deceleration']
        #motor.header.stamp = rospy.Time.now()
        return config

    def positioning_rotate(self, msg):
        rpm = msg.rpm
        acceleration = msg.acceleration
        deceleration = msg.deceleration
        self._apply_operation_method()
        time.sleep(0.1)
        self._apply_angle(msg)
        time.sleep(0.1)
        self._apply_rpm(rpm)
        time.sleep(0.1)
        # self.apply_acceleration(acceleration)
        # time.sleep(0.1)
        # self.apply_deceleration(deceleration)
        # time.sleep(0.1)
        self._start_on()
        time.sleep(0.1)
        self._off()

    def return_to_origin(self):
        self._home_on()
        time.sleep(1)
        self._off()

    def continuous_rotate(self, msg):
        rpm = msg.rpm
        reverse = msg.reverse
        self._apply_rpm(rpm)
        time.sleep(0.5)
        if(reverse):
            self._rvs_on()
        else:
            self._fwd_on()

    def _apply_operation_method(self):
        command = b"\x01\x06\x05\x01\x00\x00\xd8\xc6"
        self.client.write(bytearray(command))
        result = self.client.read(self.size)
        print("operation: {}".format(result))

    def _angle_to_bytes(self, angle):
        step = int(angle / self.pulse_angle)
        command = struct.pack(">I", step)
        return command

    def _rpm_to_bytes(self, rpm):
        hz = int(rpm / 60 * 360 / self.pulse_angle)
        command = struct.pack(">H", hz)
        return command

    def _rpm_acceleration_to_bytes(self,acceleration):
        hz = int(acceleration / 60 * 360 / self.pulse_angle)
        time = 1000 / hz * 1000
        command = struct.pack(">I", time)
        return command

    def _apply_acceleration(self,msg):
        acceleration = msg.acceleration
        command = b"\x01\x06\x06\x01" + self._rpm_acceleration_to_bytes(acceleration)
        command += self._error_check(command)
        self.client.write(command)
        result = self.client.read(self.size)
        print("acceleration set: {}".format(result))

    def _apply_deceleration(self,msg):
        deceleration = msg.deceleration
        command = b"\x01\x06\x06\x81" + self._rpm_acceleration_to_bytes(deceleration)
        command += self._error_check(command)
        self.client.write(command)
        result = self.client.read(self.size)
        print("deceleration set: {}".format(result))

    def _angle_to_bytes_rvs(self,angle):
        step = int(-angle / self.pulse_angle)
        command = struct.pack(">i", step)
        return command

    def _apply_angle(self,msg):
        angle = msg.angle
        reverse = msg.reverse
        print(msg.reverse)
        print(reverse)
        if(reverse):
            command = b"\x01\x10\x04\x00\x00\x02\x04" + self._angle_to_bytes_rvs(angle)
        else:
            command = b"\x01\x10\x04\x00\x00\x02\x04" + self._angle_to_bytes(angle)
        command += self._error_check(command)
        self.client.write(command)
        result = self.client.read(self.size)
        print("step set: {}".format(result))

    def _apply_rpm(self,rpm):
        command = b"\x01\x10\x04\x80\x00\x02\x04\x00\x00" + self._rpm_to_bytes(rpm)
        command += self._error_check(command)
        self.client.write(command)
        result = self.client.read(self.size)
        print("rpm set: {}".format(result))

    def _start_on(self):
        command = b"\x01\x06\x00\x7d\x00\x08"
        command += self._error_check(command)
        self.client.write(command)
        result = self.client.read(self.size)
        print("start on: {}".format(result))

    def _off(self):
        command = b"\x01\x06\x00\x7d\x00\x00"
        command += self._error_check(command)
        self.client.write(command)
        result = self.client.read(self.size)
        print("off: {}".format(result))

    def _fwd_on(self):
        command = b"\x01\x06\x00\x7d\x40\x00"
        command += self._error_check(command)
        self.client.write(command)
        result = self.client.read(self.size)
        print("fwd on: {}".format(result))

    def _rvs_on(self):
        command = b"\x01\x06\x00\x7d\x80\x00"
        command += self._error_check(command)
        self.client.write(command)
        result = self.client.read(self.size)
        print("rvs on: {}".format(result))

    def _home_on(self):
        command = b"\x01\x06\x00\x7d\x00\x10"
        command += self._error_check(command)
        self.client.write(command)
        result = self.client.read(self.size)
        print("home on: {}".format(result))

    def _error_check(self, query):
        crc_register = 0xFFFF
        for data_byte in bytearray(query):
            crc_register ^= data_byte
            for _ in range(8):
                overflow = crc_register & 1 == 1
                crc_register >>= 1
                if overflow:
                    crc_register ^= 0xA001
        return struct.pack("<H", crc_register)


