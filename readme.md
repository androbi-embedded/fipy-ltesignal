# Measure LTE signal strength for FiPy

Will blink the led in colors that indicate LTE signal quality. Green 
should be just ok (-12 dB), yellow better and red excelent. 
Blueish green is at the limit, blue is too low for data transfer.

Disable pybytes at startup:

import pycom
pycom.pybytes_on_boot(False)
