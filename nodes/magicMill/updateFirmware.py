''' Updates the firmware on the Magic Mill control node.

April 14th, 2019

Ilan E. Moyer
'''

from pygestalt import nodes, config
import time, sys


# ---- SYNTHETIC MODE ----
# config.syntheticModeOn() #Un-comment this line to run in synthetic mode (i.e. test mode)

# ---- DEFINE TEST NODE ----
targetNode = nodes.soloGestaltNode(name = "Magic Mill Controller", filename = "096-001b.py") #filename must be provided for synthetic mode

# ---- LOAD NEW FIRMWARE ----
targetNode.loadProgram('firmware/096-001b.hex')

# ---- RUN UNIT TESTS ----