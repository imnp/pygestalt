''' Updates the firmware on a networkedSingleStepper node.

April 14th, 2019

Ilan E. Moyer
'''

from pygestalt import nodes, config
import time, sys


# ---- SYNTHETIC MODE ----
# config.syntheticModeOn() #Un-comment this line to run in synthetic mode (i.e. test mode)

# ---- DEFINE TEST NODE ----
targetNode = nodes.networkedGestaltNode(name = "Networked Single Stepper", filename = "086-005b.py") #filename must be provided for synthetic mode

# ---- LOAD NEW FIRMWARE ----
targetNode.loadProgram('firmware/086-005b.hex')

# ---- RUN UNIT TESTS ----