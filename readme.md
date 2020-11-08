# Measure LTE signal strength with FiPy

This script will blink the FiPy led in colors that indicate LTE signal quality. Green
is the reference value, colors going towards blue represent a weaker signal, yellow
or red tones represent stronger signals. There are two blinks, the first indicates 
RSRP and the second RSRQ. For a discussion of these parameters see 
(https://www.mdpi.com/1424-8220/20/6/1636/htm).

As default values, the follwing windows for the parameters (as defined
by their center and half width values in function signal_quality()) 
are used: 

    RSRP [ -140 dBm, -90 dBm] center: -110.0 dBm
    RSRQ [ -22.5 dB, -7.5 dB] center:  -15.0 dB

That means that the led is green when the signal is 
on the center value, blue when the minimal value is 
obtained and red when the maximal value is returned. 

Values outside of the ranges are treated like the
max/min values. When the range is smaller, sensitivity around 
the center is increased.

In order to "calibrate" your ltesignal device, leave it connected
with the console and run it at a location with "normal" or
"reference" signal. Leave it running for a while (a couple of 
minutes) and use the last two values of the last data row (mean 
values `<rsrp>` and `<rsrq>`) 

    rsrp,rsrq,<rsrp>,<rsrq> -107.29 -14.44 -107.7893 -14.724375

as new center values by setting

    signal_quality(rsrp_center=-107.8, rsrq_center=-14.7, show_status=True) 

in the main program. The new reference value will now be shown
as pure green, a better signal will give more yellowish/redish 
color tones, a worser signal gives green with blue tones or blue. 

For my antenna (pycom 2016.08.18 rev.02) and location (a small town close 
to Seville, Spain), values are around -108 dBm and -15 dB at my working place
which is just on the verge of dropping data.

The modem command does not always return signal strength values,
so longer pauses between the blinking of the leds are normal.
It would be easy to add a wifi access point to the code so you can
see the precise values that are printed to the log
with a telnet session. You could also easily send them online.

I am just starting to learn LTE so I don't know if this program incurs
data usage, be careful just in case.

Disable pybytes at startup:

    import pycom
    pycom.pybytes_on_boot(False)

Have fun!