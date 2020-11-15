import socket
# use this for the Vodafone SIM sold by pycom, comment out otherwise
socket.dnsserver(0,"172.31.16.100")
socket.dnsserver(1,"172.31.32.100")
# parameters for the lte.attach
ATTACH_PARAMETERS={"band": 20, "apn": "pycom.io"}
import time
import re
import sys
import network
import pycom
import math

def at_match(lte,cmd,reg_expr,n_groups=0):
    lines = lte.send_at_cmd(cmd)
    match = re.search(reg_expr, lines)
    if n_groups==0:
        return match != None
    if match:
        result = []
        for i in range(n_groups):
            result.append(match.group(i+1))
        return result
    else:
        # print("no match:",lines)
        return []

def signal_quality(rsrp_center=-110, rsrp_hw=15, rsrq_center=-15, rsrq_hw=7.5,
    ntest = 10, show_status=False, reset = False, sensitivity=False):
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
        if reset:
            print("reset lte")
            lte.reset()
    except OSError:
        print('cannot init/reset lte. power cycle your device.')
        sys.exit()
    lte.init()
    # set n=2 in cereg. the code in lte seems to require n to be set to 2 without
    # ever setting it when using "legacy" mode - see lte_check_attached() in 
    # https://github.com/pycom/pycom-micropython-sigfox/blob/master/esp32/mods/modlte.c)
    # In my case I could not attach when n!=2. I am not sure I am using legacy mode though.
    cereg=at_match(lte,'AT+CEREG?',"\+CEREG:\s([0-9]+),([0-9]+)",2)
    if len(cereg)==2:
        if int(cereg[0])!=2:
            print("fixing cereg=2:",cereg)
            if not at_match(lte,'AT+CEREG=2',"\s*OK\s*"):
                print('could not set n=2 with CEREG.')
                sys.exit()
            cereg=at_match(lte,'AT+CEREG?',"\+CEREG:\s([0-9]+),([0-9]+)",2)
        print("cereg",cereg)
    if show_status:
        print("attaching..")
    lte.attach(**ATTACH_PARAMETERS)
    oldstat=(None,None) 
    while not lte.isattached():
        time.sleep(0.25)
        if show_status:
            print('.',end='')
            res = lte.send_at_cmd('AT!="fsm"')
            match = re.search(r'RRC\sTOP\sFSM\s*\|([A-Z_]*)\s*\|\s*\|\s*RRC\sSEARCH\sFSM\s*\|([A-Z_]*)\s*', res) 
            if match:
                stat = (match.group(1), match.group(2))
                if stat != oldstat:
                    print("\n", stat, end='')
                    oldstat = stat
    if show_status:
        print("attached!")
    pycom.heartbeat(False)
    # three short green blinks -> we are attached
    for _ in range(3):
        pycom.rgbled(0x00ff00)
        time.sleep(0.15)
        pycom.rgbled(0)
        time.sleep(0.05)
    time.sleep(2)
    # main loop to measure signal strength
    for _ in range(ntest):
        res = lte.send_at_cmd('AT!="showphy"')
        if res.find('CELL_ACQUIRED') != -1:
            match = re.search(r'RSRP\s\(dBm\)\s*:\s*(-?[0-9]*\.[0-9]*)\s*RSRQ\s\s\(dB\)\s*:\s*(-?[0-9]*\.[0-9]*)', res) 
            rsrp = 0.0
            rsrq = 0.0
            if match:
                no_cell = 0
                rsrp = float(match.group(1))
                rsrq = float(match.group(2))
                # accumulated mean values
                rsrp_mean = rsrp_mean + rsrp
                rsrq_mean = rsrq_mean + rsrq
                valid_data = valid_data + 1
                print("rsrp,rsrq,<rsrp>,<rsrq>:",rsrp,rsrq,rsrp_mean/valid_data,rsrq_mean/valid_data)    
                # 1st blink: rsrp
                color_strength(rsrp, rsrp_min, rsrp_max, sensitivity)
                time.sleep(0.5)
                # 2nd blink: rsrq
                color_strength(rsrq, rsrq_min, rsrq_max, sensitivity)
            else:
                print("no match")
        else:
            no_cell = no_cell + 1
            match = re.search(r'Synchro\sstate\s*:\s*([a-zA-Z0-9_]+[\s]?[a-zA-Z0-9]+)', res)
            if show_status:
                if match:
                    print(match.group(1))
                else:
                    print('.',end='')

            if (no_cell > 20):
                if match.group(1)=="OFF":
                    sys.exit()
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

def color_strength(val, minval, maxval, sensitivity=False):
    """ display signal strength or quality on led blue=bad green=normal red=super """
    # restrict to range [minval,maxval]
    if val < minval:
        val = minval
    if val > maxval:
        val = maxval
    # low .. middle .. high colors
    colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0)]  # [BLUE, GREEN, RED]
    # calculate color index
    if sensitivity:
        # translate to symmetric [min , max] -> [-val , +val] 
        midpoint = minval + (maxval-minval)/2
        val_center = val - midpoint
        # apply sensivity function: -> [0 , 1]
        r, g, b = convert_to_rgb(0.0, 1.0, sigmoid(val_center), colors)
    else:
        r, g, b = convert_to_rgb(minval, maxval, val, colors)
    # print('{:.3f} -> ({:3d}, {:3d}, {:3d})'.format(val, r, g, b))
    color = r << 16 | g << 8 | b
    # show on led
    pycom.rgbled(color)
    time.sleep(0.25)
    pycom.rgbled(0)

EPSILON = calc_eps()
def convert_to_rgb(minval, maxval, val, colors):
    """ convert a numerical value to rgb color values """ 
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
signal_quality(rsrp_center=-107.8, rsrq_center=-14.7, 
    show_status=True, reset=True) 
