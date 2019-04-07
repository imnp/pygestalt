""" Arduino-based Communications Rate Tester

This virtual node serves two purposes:
1. To aid in checking how quickly bi-directional packet exchanges can be executed with an arduino-based node.
2. To determine the influence of packet length on communications rate. It is expected that for short packets,
   the dominating factor will be time spent within the layers of the controlling computer's operating system.
   However, for longer packets, the time spent in actual transmission will dominate.

Note that some arduinos are based on an FT232, and those will more closely mirror the expected rates on a
standard FABNET-based Gestalt network.

April 5th, 2019
Ilan E. Moyer
"""

from pygestalt import nodes # for access to the gestalt virtual node base classes
from pygestalt import core  # for access to the actionObject class for creating service routines
from pygestalt import packets # for access to the packet templates and encoding types
import time #for synthetic mode

class virtualNode(nodes.arduinoGestaltVirtualNode):
    
    def init(self, *args, **kwargs):
        """Initialiation method for the virtual node instance."""
        self.gestaltPacketBaseSize = 6 #bytes. The length of the standard Gestalt packet wrapper, including header, length byte, and checksum.
        self.maxPayloadSize = 255 - self.gestaltPacketBaseSize #the maximum length of a test payload, in bytes
    
    def initPackets(self):
        """Initialize packet types."""

        self.outboundTestPacket = packets.template('outboundTestPacket',
                                                    packets.pList('testBytes')) #payload is a list of unfixed length
        self.inboundTestPacket = packets.template('inboundTestPacket',
                                                    packets.pList('testBytes')) #payload is a list of unfixed length
    
    def initPorts(self):
        """Bind functions to ports and associate with packets."""

        self.bindPort(port = 10, outboundFunction = self.exchangeTestPacket, outboundTemplate = self.outboundTestPacket,
                      inboundTemplate = self.inboundTestPacket)
    
    # ---- SERVICE ROUTINES ----
    
    class exchangeTestPacket(core.actionObject):
        """Exchanges a test packet with the physical node"""
        def init(self, outboundPayloadLength, inboundPayloadLength):
            """Initializes the actionObject.
            
            outboundPayloadLength -- The number of payload bytes to transmit to the physical node. Must be less than 249.
            inboundPayloadLength -- the number of payload bytes to transmit back to the virtual node. Must be less than 249.

            Returns totalOutboundLength, totalInboundLength
                totalOutboundLength -- the total length in bytes of the outbound packet (including headers, checksum, etc)
                totalInboundLength -- the total length in bytes of the inbound packet (including headers, checksum, etc), or
                                      False if no return packet was received.
            """
            maxPayloadLength = 249
            
            if outboundPayloadLength > self.virtualNode.maxPayloadSize or inboundPayloadLength > self.virtualNode.maxPayloadSize:
                notice(self, "Requested test packet payload exceeds maximum size of " + str(self.virtualNode.maxPayloadSize) + " bytes.")
                return False, False
            
            outboundPayload = [inboundPayloadLength for byte in range(outboundPayloadLength)] #encode the return packet length as the payload
                                                                                              #bytes of the outbound packet
            self.setPacket(testBytes = outboundPayload)
  
            totalOutboundLength = outboundPayloadLength + self.virtualNode.gestaltPacketBaseSize
            
            if self.transmitUntilResponse(): #Transmits multiple times if necessary until a reply is received from the node.
                totalInboundLength = len(self.getPacket()) + self.virtualNode.gestaltPacketBaseSize
                return totalOutboundLength, totalInboundLength #A response was received, so indicate the command was executed by returning True.
            else: #No response was received, in spite of multiple attempts.
                notice(self.virtualNode, 'did not receive an inbound test packet') #generate a notice to the user.
                return totalOutboundLength, False
        
        def synthetic(self, testBytes):
            if len(testBytes): #non-zero test packet length
                responsePayloadLength = testBytes[0] #the length of the response payload is encoded in the outbound packet
            else:
                responsePayloadLength = 0
            responseTestBytes = range(responsePayloadLength)
            return {'testBytes':responseTestBytes}