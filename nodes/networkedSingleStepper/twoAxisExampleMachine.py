# TWO AXIS EXAMPLE MACHINE
#
# FEBRUARY 21st, 2020
#
# This virtual machine is a testbed for implementing synchronization in pyGestalt 0.7

# ----- IMPORTS -----
from pygestalt import nodes, interfaces, config, machines, mechanics, units
import time
import sys
import random
import math

class virtualMachine(machines.virtualMachine):
    
    def init(self, *args, **kwargs):
        """General initialization method for the virtual machine.
        
        This method gets called first, before any of the more specific initializations occur.
        
        Any arguments passed to the virtual machine on instantiation will be delivered as arguments to this function.
        """
        pass


    def defaultInterface(self):
        """Provides a default interface to the virtual machine, to be used if none is provided on instantiation.
        
        This method should return a gestaltInterface.
        """
        # DEFINE A SERIAL INTERFACE TO COMMUNICATE WITH THE FABNET BUS  
        serialInterface = interfaces.serialInterface(baudrate = 115200, interfaceType = 'ftdi')
        # DEFINE A GESTALT INTERFACE FOR TALKING TO THE NODES
        gestaltInterface = interfaces.gestaltInterface(name = "stepperGestaltInterface", interface = serialInterface, persistence = "twoAxisExample.vmp")
        # RETURN THE GESTALT INTERFACE
        return gestaltInterface
           
    def initNodes(self):
        """Initialize all nodes in the virtual machine."""
        self.compoundNode = nodes.pattern(2, interface = self.interface, filename = "086-005b.py")

    def initMechanics(self):
        pass
        
    def initLast(self):
        pass
    

if __name__ == "__main__":
#     config.syntheticModeOn()
#     config.verboseDebugOn()
    myVirtualMachine = virtualMachine()
#     myVirtualMachine.compoundNode.setMotorCurrent((1.0, 1.2))
    myVirtualMachine.compoundNode.stepRequest((100,200), 200*256)
    myVirtualMachine.compoundNode.stepRequest((-100,-200), 200*256)
    while True:
        print myVirtualMachine.compoundNode.getPositionRequest()
        time.sleep(1)
#     myVirtualMachine.compoundNode.loadProgram('firmware/086-005b.hex')
    time.sleep(0.5)