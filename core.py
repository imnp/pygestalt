#   pyGestalt Core Module

"""Provides the central elements of the pyGestalt framework."""

#--IMPORTS--
import copy

class actionObject(object):
    """A token that embodies the logic behind packet generation.
    
    actionObjects serve a dual role. They contain a set of functions written by the node designer
    that create and interpret packet communication between the virtual and real nodes. They also
    serve as a carrier for the packet as it makes its winding way thru the gestalt framework on
    its way to the interface with the real node. Each call to the action object subclass will generate
    an actionObject dedicated to converting the call into a packet, with the option of also handling a returned
    packet. The reason for bundling a packet with the logic used to create it is that this permits the packet to
    change after it has been generated but before being transmitted. One particular case where this behavior is
    useful is in synchronizing multiple nodes even though the function calls to the nodes are made sequentially.
    In this case synchronization calculations can occur once all of the participant actionObjects are generated.
    
    One of the key differences between this and the previous version of Gestalt (v0.6) is that previously
    actionObjects needed to be wrapped in a serviceRoutine. This is being sidestepped by using class
    properties along with instance properties.
    """
    
    #Explicitly define class parameters here. These get set to real values when the actionObject is bound to a port by
    #nodes.baseGestaltNode.bindPort(). In reality these aren't overwritten but act as fallbacks that are superseded by child class attributes.
    _port_ = None
    _inboundPacketFlag_ = None  #Note that this flag is set dynamically, so need to be careful about which instance is monitoring it.
    _outboundTemplate_ = None
    _inboundTemplate_ = None
    _baseActionObject_ = None
    virtualNode = None
    
    def __new__(cls, *args, **kwargs):
        """Intantiation routine for actionObject base class.
        
        When a call is made to the action object class, this "magic" function creates the instance.
        Any arguments are passed along to the subclass's init() function, which may either return a value or None.
        If nothing is returned, as is the case in typical __init__ methods, then we return the actionObject. But
        if a return value is provided by the user (i.e. the interpreted reply of a real node), this is passed along.
        """
        newActionObject = object.__new__(cls)   #creates the new actionObject
        newActionObject._init_()    #runs the actionObject base class's initialization. Note that
                                    #__init__ is intentionally not used, because otherwise it would get called twice.
        returnValue = newActionObject.init(*args, **kwargs) # calls the user-defined initialization routine, this time 
                                                            # with any provided arguments.
        
        if returnValue == None:     #if the user initialization doesn't return anything, then return the actionObject
            return newActionObject
        else:                       #otherwise pass along whatever the user has provided
            return returnValue
        
    def _init_(self):
        """actionObject initialization method.
        
        Note that no arguments are provided because user-supplied arguments are handled strictly by the subclass's init() method.
        """
        self._outboundPacketDictionary_ = {}    #stores key:value pairs to be encoded by _encodeOutboundPacket_
        self._inboundPacketDictionary_ = {} #stores key:value pairs decoded by _decodeAndSetInboundPacket_
        
    def init(self, *args, **kwargs):    #user initialization routine. This should get overridden by the subclass.
        """actionObject subclass's initialization routine.
        
        This should be overridden by the user-defined subclass."""
        pass
    
    def setPacket(self, **kwargs):
        """Updates the dictionary that will encode the actionObject's outgoing packet using the provided keyword arguments.
        
        **kwargs -- all of the key:value pairs to be encoded are provided as keyword arguments to the function.
        """
        self._outboundPacketDictionary_.update(kwargs)
        return True
    
    def getPacket(self):
        """Returns the decoded inbound packet, or None if no inbound packet has been received."""
        if self._inboundPacketDictionary_ == {}:
            return None
        else:
            return copy.copy(self._inboundPacketDictionary_)
    
    def _getEncodedOutboundPacket_(self):
        """Internal function that encodes and returns the actionObject's outgoing packet dictionary using the outbound packet template."""
        return self._outboundTemplate_.encode(self._outboundPacketDictionary_)
    
    def _decodeAndSetInboundPacket_(self, serializedPacket):
        """Internal function that decodes and stores an inbound serialized packet using the inbound packet template.
        
        serializedPacket -- a packets.serializedPacket object containing a serial byte sequence that should be decoded and stored.
        """
        self._inboundPacketDictionary_ = self._inboundTemplate_.decode(serializedPacket)[0]    #decodes serializedPacket using _inboundTemplate_
        return True
    
    def _synthetic_(self, toSyntheticNodeSerializedPacket):
        """Internal function that encodes and decodes packets en-route to user-provided synthetic service routine to support operation without physical nodes attached.
        
        toSyntheticNodeSerializedPacket -- a serialized packet that is being rerouted to a synthetic service routine instead of out to a physical node.
        
        New to Gestalt 0.7 is a debug mode where synthetic physical nodes can be used in leu of real ones. If the user wants to support this, they
        need to write a function called 'synthetic' that pretends to be a service routine on the physical node. The purpose of _synthetic_ is to
        provide encode/decode services for the user-provided synthetic function.

        This function will call synthetic with a decoded dictionary, and will return an encoded version of the reply.
        """
        decodedPacket = self._outboundTemplate_.decode(toSyntheticNodeSerializedPacket)[0] #decode the incoming serialized packet
        replyDictionary = self.synthetic(**decodedPacket) #call synthetic using decoded packet dictionary as the keyword arguments.
        return self._inboundTemplate_.encode(replyDictionary) #return the encoded reply from synthetic
    
    def synthetic(self, **kwargs):
        """Default synthetic service routine function.
        
        **kwargs -- when rewritten by the user, these should be named parameters that the synthetic service routine accepts.
        
        This function should be replaced by the user, and simulates the physical node's service routine.
        
        Returns None if user did not provide a synthetic service routine, or if no reply should be sent.
        Otherwise returns a dictionary of values to get encoded and sent back to the virtual node.
        """
        return None
    
    def transmit(self, mode = 'unicast'):
        """Transmits packet on the virtualNode's interface.
        
        mode -- the transmission mode, either 'unicast to direct at a single node, or 'multicast' to direct at all nodes.
        
        *Add description here as build out priority and channel access queues.
        """
        
        ###The following code should get replaced... just for fleshing out the synthetic functions for now!
        self._decodeAndSetInboundPacket_(self._synthetic_(self._getEncodedOutboundPacket_()))   #directly connects transmit to synthetic
        return True        
    
    def transmitUntilReply(self, timeout = 0.2, mode = 'unicast', attempts = 10):
        """Persistently transmits until a reply is received from the node.
        
        timeout -- the time (in seconds) to wait for a reply between re-attempts
        mode -- the transmission mode, either 'unicast' to direct at a single node, or 'multicast' to direct at all nodes
        attempts -- the number of transmission attempts before giving up.
        
        This is an area in which to potentially improve Gestalt, by building in some functionality that
        can identify and respond intelligently to when a node goes down.
        """
        self.transmit(mode = mode)
        return True

#--- GENERIC ACTION OBJECTS ---
class genericActionObject(actionObject):
    """A perfectly generic actionObject type."""
    pass

class genericOutboundActionObjectBlockOnReply(actionObject):
    """A generic actionObject type designed to transmit and block until a reply is received."""
    pass

class genericOutboundActionObject(actionObject):
    """A generic actionObject type designed to transmit (but not block)."""
    pass

class genericInboundActionObject(actionObject):
    """A generic actionObject type designed to receive."""
    pass