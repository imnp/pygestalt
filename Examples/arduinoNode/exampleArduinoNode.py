""" A virtual node for communicating with an example Arduino Uno based physical node.

Written 12/7/15 by Ilan E. Moyer
"""

#---- IMPORTS -----
from pygestalt import nodes # for access to the gestalt virtual node base classes
from pygestalt import core  # for access to the actionObject class for creating service routines

class virtualNode(nodes.arduinoGestaltVirtualNode):
    """The exampleArduinoNode virtual node."""
    # This class should be named 'virtualNode for the import machinery to function properly. There are several options
    # of base classes here, but nodes.arduinoGestaltVirtualNode will set up the serial interface automatically and use
    # the correct baud rate. This is only done because the node type is so well known. Generally it is left to the user
    # to instantiate the terminal interface (e.g. a serial port)
    
    def init(self, *args, **kwargs):
        """Initialiation method for the virtual node instance."""
        # User initialization routine for defining optional constants and parameters that are specific to the node hardware.
        # Examples miht be the crystal frequency, or an ADC reference voltage. During initialization this method gets called
        # before the other init methods below.
        # Note that you can replace *args and **kwargs with any positional or named arguments that you want your node to
        # accept.
        
        self.crystalFrequency = 16000000    #MHz
        self.ADCReferenceVoltage = 5.0  #Volts