""" A virtual node for communicating with an example Arduino Uno based physical node.

Written 3/22/19 by Ilan E. Moyer
"""

#---- IMPORTS -----
from pygestalt import nodes # for access to the gestalt virtual node base classes
from pygestalt import core  # for access to the actionObject class for creating service routines
from pygestalt import packets # for access to the packet templates and encoding types

class virtualNode(nodes.arduinoGestaltVirtualNode):
    """The arduino_basicNode virtual node."""
    # This class should be named 'virtualNode for the import machinery to function properly. There are several options
    # of base classes here, but nodes.arduinoGestaltVirtualNode will set up the serial interface automatically and use
    # the correct baud rate. This is only done because the node type is so well known. Generally it is left to the user
    # to instantiate the terminal interface (e.g. a serial port)
    
    def init(self, *args, **kwargs):
        """Initialiation method for the virtual node instance."""
        # User initialization routine for defining optional constants and parameters that are specific to the node hardware.
        # Examples might be the crystal frequency, or an ADC reference voltage. During initialization this method gets called
        # before the other init methods below.
        # Note that you can replace *args and **kwargs with any positional or named arguments that you want your node to
        # accept.
        
        self.crystalFrequency = 16000000    #MHz
        self.ADCReferenceVoltage = 5.0  #Volts
    
    def initPackets(self):
        """Initialize packet types."""
        # As a communications framework, one of the primary tasks of pyGestalt is to make it easier to pass various data types
        # back and forth between the virtual node and the firmware running on the physical node. A rich set of data types
        # is defined in the packets submodule.
        
        # Below is packet template comprised of an unsigned integer value, encoded in a single byte.
        # The first argument is a name for the template, followed by as many types as are needed.
        # You can find all of the avaliable types in the packets sub-module.
        self.LEDControlRequestPacket = packets.template('LEDControlRequest',
                                                           packets.unsignedInt('command',1)) #(type name, number of encoded bytes)
    
    def initPorts(self):
        """Bind functions to ports and associate with packets."""
        # In order for service routine functions in the virtual node to communicate with the service routines on physical node, they 
        # must both have a commonly shared identifier (referred to in pyGestalt as a port), and a common understanding of how transmitted 
        # information is encoded. self.bindPort() "binds" virtual node service routines to port numbers, and then associated them with the 
        # packet templates that are used to encode and decode transmitted communication packets. With these associations in place, 
        # pyGestalt is able to automatically assist in shuttling messages in the correct format between virtual and physical nodes.
        
        # Note that if an inbound packet template is not specified in the bindPort() call, any inbound packets received on the port 
        # will be assumed to contain no payload.
        self.bindPort(port = 10, outboundFunction = self.LEDControlRequest, outboundTemplate = self.LEDControlRequestPacket)
    
    
    # ---- PUBLIC USER FUNCTIONS ----
    # Here is the place for functions that are explicitly intended for the user to call. These are useful in situations like our LED demo, 
    # where the user might want to simply call ledOn() or ledOff(), rather than calling the service routine that actually transmits the 
    # command to the physical node.
    
    def ledOn(self):
        """Turns on the LED on the physical node."""
        return self.LEDControlRequest(True) #simply calls the virtual node service routine with a True (meaning "on") argument
    
    def ledOff(self):
        """Turns off the LED on the physical node."""
        return self.LEDControlRequest(False) #calls the virtual node service routine with a False (meaning "off") argument
    
    
    # ---- SERVICE ROUTINES ----
    # Virtual node service routines are functions that are responsible for communicating with complementary service routines on
    # the physical node. These special functions are actually children of the actionObject base class. We won't go into all of
    # the details here, but pyGestalt follows a pattern where calls to service routines do not simply generate encoded packets.
    # Rather, an actionObject is generated and preserved until the very moment before transmission, at which point it spits out
    # an encoded packet. The short reason for this is that for more complicated controls applications, such as those requiring
    # motion planning, the final output of the function might change well after it is called.
    
    class LEDControlRequest(core.actionObject):
        """Controls the state of the node's indicator LED."""
        def init(self, ledState):
            """Initializes the actionObject.
            
            ledState -- a boolean value, where True will turn on the LED, and False will turn it off.

            Returns True if a confirmation packet was received, or False if not.
            """
            if ledState:
                self.setPacket(command = 1)
            else:
                self.setPacket(command = 0)
                            
            if self.transmitUntilResponse(): #Transmits multiple times if necessary until a reply is received from the node.
                return True #A response was received, so indicate the command was executed by returning True.
            else: #No response was received, in spite of multiple attempts.
                notice(self.virtualNode, 'got no respone to LED control request') #generate a notice to the user.
                return False
        