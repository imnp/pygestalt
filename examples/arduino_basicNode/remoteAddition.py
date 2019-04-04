"""A quick script to demonstrate how you can import and call functions on virtual nodes from within a Python program.

Written 4/3/2019 by Ilan E. Moyer
"""

import arduino_basicNode as arduino #import the virtual node module, with an easier name
import sys #for getting input arguments

inputValues = sys.argv  #contains all of the arguments provided when the script was called.

value1 = float(sys.argv[1]) #first input argument, converted from string to float
value2 = float(sys.argv[2]) #second input argument, converted from string to float

myArduino = arduino.virtualNode()
print myArduino.sumNumbers(value1, value2)
