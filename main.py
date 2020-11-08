import socket
# modify the lte.attach command for your SIM
# use this for the Vodafone SIM sold by pycom
socket.dnsserver(0,"172.31.16.100")
socket.dnsserver(1,"172.31.32.100")
import time
import re
import network
import pycom
import math

def signal_quality(show_status=False, show_at=False, sensitivity=False):
    """ attach to LTE and then query signal quality """
    pycom.heartbeat(True)
    lte = network.LTE()
    lte.reset()
    lte.init()
    lte.attach(band=20, apn="pycom.io") 
    if show_status:
        print("attaching..",end='')
    while not lte.isattached():
        time.sleep(0.25)
        if show_status:
            print('.',end='')
        if show_at:
            print(lte.send_at_cmd('AT!="fsm"'))         # get the System FSM
    if show_status:
        print("attached!")
    
    pycom.heartbeat(False)
    while True:
        res = lte.send_at_cmd('AT!="showphy"')
        match = re.search(r'RSRQ\s\s\(dB\)\s*:\s*(-?[0-9]*\.[0-9]*)', res) 
        rsrq = 0.0
        if match:
            rsrq = float(match.group(1))
        color_strength(rsrq, sensitivity)
        time.sleep(1.0)

def calc_eps():
    """ calculate machine epsilon """
    eps = 1.0
    while eps + 1 > 1:
        eps /= 2
    eps *= 2
    return eps

def sigmoid(x):
    """ sigmoid function, see https://en.wikipedia.org/wiki/Sigmoid_function """
    return 1.0/(1.0 + math.exp(-x))

def color_strength(rsrq, sensitivity=False):
    """ display signal quality on led blue=bad green=okish red=super """
    print("rsrq:",rsrq)
    # restrict to range -21..-3
    minval, maxval = -21.0, -3.0 # -12.0 is midpoint
    if rsrq < minval:
        rsrq = minval
    if rsrq > maxval:
        rsrq = maxval
    # low .. middle .. high colors
    colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0)]  # [BLUE, GREEN, RED]
    # calculate color index
    if sensitivity:
        # apply sensitivity function: shift [-21 , -3] -> [-9 , 9] -> [0 , 1]
        rsrq_center = rsrq + 12.0
        r, g, b = convert_to_rgb(0.0, 1.0, sigmoid(rsrq_center), colors)
    else:
        r, g, b = convert_to_rgb(minval, maxval, rsrq, colors)
    # print('{:.3f} -> ({:3d}, {:3d}, {:3d})'.format(rsrq, r, g, b))
    color = r << 16 | g << 8 | b
    # show on led
    pycom.rgbled(color)
    time.sleep(0.25)
    pycom.rgbled(0)

EPSILON = calc_eps()
def convert_to_rgb(minval, maxval, val, colors):
    # see https://stackoverflow.com/questions/20792445/calculate-rgb-value-for-a-range-of-values-to-create-heat-map
    i_f = float(val-minval) / float(maxval-minval) * (len(colors)-1)
    i, f = int(i_f // 1), i_f % 1  # Split into whole & fractional parts.
    if f < EPSILON:
        return colors[i]
    else:  # Otherwise return a color within the range between them.
        (r1, g1, b1), (r2, g2, b2) = colors[i], colors[i+1]
        return int(r1 + f*(r2-r1)), int(g1 + f*(g2-g1)), int(b1 + f*(b2-b1))

time.sleep(2)
# use sensitivity=True for more sensivity around -12 dB
signal_quality(show_status=True, sensitivity=False) 
