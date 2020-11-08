import socket
# modify the lte.attach command for your SIM
# use this for the Vodafone SIM sold by pycom
socket.dnsserver(0,"172.31.16.100")
socket.dnsserver(1,"172.31.32.100")
import time
import re
import sys
import network
import pycom
import math

def signal_quality(rsrp_center=-110, rsrp_hw=15, rsrq_center=-15, rsrq_hw=7.5,
    show_status=False, show_at=False, sensitivity=False):
    """ attach to LTE and then query signal quality """
    # init mean values
    rsrp_mean=0.0
    rsrq_mean=0.0
    valid_data=0
    no_cell=0
    # calculate intervals and optionally display
    rsrp_min=rsrp_center - rsrp_hw
    rsrp_max=rsrp_center + rsrp_hw
    rsrq_min=rsrq_center - rsrq_hw
    rsrq_max=rsrq_center + rsrq_hw
    if show_status:
        print("rsrp [",rsrp_min,",",rsrp_max,"] center:",rsrp_center)
        print("rsrq [",rsrq_min,",",rsrq_max,"] center:",rsrq_center)
    # init and attach
    pycom.heartbeat(True)
    if show_status:
        print("init lte")
    try:
        lte = network.LTE()
        lte.reset()
    except OSError:
        print('cannot init/reset lte. switch your device off and on again.')
        sys.exit()
    lte.init()
    if show_status:
        print("attaching",end='')
    lte.attach(band=20, apn="pycom.io") 
    while not lte.isattached():
        time.sleep(0.25)
        if show_status:
            print('.',end='')
        if show_at:
            print(lte.send_at_cmd('AT!="fsm"'))         # get the System FSM
    if show_status:
        print("attached!")
    pycom.heartbeat(False)
    for _ in range(3):
        pycom.rgbled(0x00ff00)
        time.sleep(0.15)
        pycom.rgbled(0)
        time.sleep(0.05)
    time.sleep(2)
    while True:
        res = lte.send_at_cmd('AT!="showphy"')
        #print(res)
        if res.find('CELL_ACQUIRED') != -1:
            match = re.search(r'RSRP\s\(dBm\)\s*:\s*(-?[0-9]*\.[0-9]*)\s*RSRQ\s\s\(dB\)\s*:\s*(-?[0-9]*\.[0-9]*)', res) 
            rsrp = 0.0
            rsrq = 0.0
            if match:
                no_cell = 0
                rsrp = float(match.group(1))
                rsrq = float(match.group(2))
                rsrp_mean = rsrp_mean + rsrp
                rsrq_mean = rsrq_mean + rsrq
                valid_data = valid_data + 1
                print("rsrp,rsrq,<rsrp>,<rsrq>",rsrp,rsrq,rsrp_mean/valid_data,rsrq_mean/valid_data)    

                color_strength(rsrp, rsrp_min, rsrp_max, sensitivity)
                time.sleep(0.5)
                color_strength(rsrq, rsrq_min, rsrq_max, sensitivity)
            else:
                print("no match")
        else:
            no_cell = no_cell + 1
            match = re.search(r'Synchro\sstate\s*:\s*([a-zA-Z0-9_]+[\s]?[a-zA-Z0-9]+)', res) 
            if match:
                print(match.group(1))
            else:
                print('.',end='')

            if (no_cell > 20): # do something so packets are sent
                if match.group(1)=="OFF":
                    sys.exit()
                #no_cell = 0
                #res = lte.send_at_cmd('AT+PING="172.31.16.100",1,32')
        time.sleep(2.0)

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

def color_strength(rsrq, minval, maxval, sensitivity=False):
    """ display signal strength or quality on led blue=bad green=okish red=super """
    # restrict to range -21..-3
    # minval, maxval = -21.0, -3.0 # -12.0 is midpoint
    midpoint = minval + (maxval-minval)/2
    if rsrq < minval:
        rsrq = minval
    if rsrq > maxval:
        rsrq = maxval
    # low .. middle .. high colors
    colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0)]  # [BLUE, GREEN, RED]
    # calculate color index
    if sensitivity:
        # apply sensitivity function: shift [min , max] -> [-val , +val] -> [0 , 1]
        rsrq_center = rsrq - midpoint
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

print("Starting ..")
time.sleep(2)
signal_quality(rsrp_center=-107.8, rsrq_center=-14.7, show_status=True) 
