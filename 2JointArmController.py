#!/usr/bin/env python2

MAX_SPEED = 200

# --- Library Includes ---

# evdev for joysticks
import evdev
from evdev import ecodes

# Other libraries
import threading
import pyudev
import os


# --- EV3 Classes ---

PYUDEV_CONTEXT = pyudev.Context()

import ev3

# --- Joystick Reading Code ---

JOYSTICK = None
JOYSTICK_CAPS = {}
JOYSTICK_STATE = {}
JOYSTICK_DEFAULT_STATE = 0.0
#304-BTN_A
#305-BTN_B
#306-BTN_C
#307-BTN_NORTH

#545/546/547/544-BTN_DPAD_(DOWN/UP/LEFT/RIGHT)
def map_range(in_min, in_max, out_min, out_max, value):
    return out_min + ((value - in_min) * (out_max - out_min) / (in_max - in_min))

def find_joystick(name):
    global JOYSTICK
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    JOYSTICK = [device for device in devices if device.name == name][0]
    for abs_id, abs_info in JOYSTICK.capabilities()[ecodes.EV_ABS]:
        JOYSTICK_CAPS[abs_id] = abs_info
        JOYSTICK_STATE[abs_id] = JOYSTICK_DEFAULT_STATE

def watch_joystick():
    for event in JOYSTICK.read_loop():
        #print(event.code)
        #312/2 for press and release of left trigger
        #313/5 for press and release of right trigger
        #ABS_RZ =5 
        #ABS_Z=2
        if event.type == ecodes.EV_ABS:
            caps = JOYSTICK_CAPS[event.code]
            JOYSTICK_STATE[event.code] = map_range(caps.min, caps.max, -1.0, 1.0, event.value)
            if abs(JOYSTICK_STATE[event.code])<0.05:JOYSTICK_STATE[event.code] = 0
import math as m
armZeroed = False
def armController(x,y,shoulder,elbow,shoulderLimit,elbowLimit):
    a1=11.5
    a2=8
    global armZeroed
    if armZeroed:
        q2 = int(-(m.degrees(m.acos(((x**2) + (y**2) -(a1**2)-(a2**2))/(2*a1*a2)))))
        q1 = int(m.degrees(m.atan2(y,x)+m.atan2((a2*m.sin(q2)),(a1+a2*m.cos(q2)))))
        #print('q1(shoulder) ='+str(q1) + ' q2(elbow) =' + str(q2))
        elbow.moveAbs(5*(180+q2),200)
        shoulder.moveAbs(5*(q1-90),200)
    else:
        elbow.run(-50)
        shoulder.run(50)
        if elbowLimit.getValue()==1 and shoulderLimit.getValue()==1:
            elbow.reset()
            shoulder.reset()
            elbow.braking(True)
            shoulder.braking(True)
            armZeroed = True

# --- Main Code ---
if __name__ == '__main__':
    print('Initializing motors')
    claw = ev3.motor('A')
    elbow = ev3.motor('B')
    shoulder = ev3.motor('C')
    turret = ev3.motor('D')
    elbowLimit = ev3.sensor('1')
    elbowLimit.touch()
    shoulderLimit = ev3.sensor('2')
    shoulderLimit.touch()
    print('Discovering joystick')

    # 'Wireless Controller' for PS4

    find_joystick('Wireless Controller')
    joystick_thread = threading.Thread(target=watch_joystick)
    joystick_thread.daemon = True
    joystick_thread.start()

    print('Starting drive loop')
    x=4
    y=4
    try:
        while True:
            ls_y = -JOYSTICK_STATE[ecodes.ABS_Y]
            rs_y = -JOYSTICK_STATE[ecodes.ABS_RY]
            rt = 1+JOYSTICK_STATE[ecodes.ABS_RZ]
            lt = 1+JOYSTICK_STATE[ecodes.ABS_Z]
            if rt !=0 and lt !=0: 
                turret.run(0)
            else:
                turret.run(int((rt-lt))*MAX_SPEED)#lazy logic to avoid comparators
            armController(x,y,shoulder,elbow,shoulderLimit,elbowLimit)
            print ('x =' + str(x) + ' y ='+ str(y))
            x+=ls_y*.1
            y+=rs_y*.1
            if x>7:x=7
            if y>10:y=10

    finally:
        claw.braking(False)
        claw.run(0)
        elbow.braking(False)
        elbow.run(0)
        shoulder.braking(False)
        shoulder.run(0)
        turret.braking(False)
        turret.run(0)
