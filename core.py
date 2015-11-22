#   pyGestalt Core Module

"""Provides the central elements of the pyGestalt framework."""

#--IMPORTS--
import copy
import threading
from pygestalt.utilities import notice

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
    #nodes.baseGestaltNode.bindPort(). In reality these aren't overwritten but act as fallbacks that are superseded by derived class attributes.
    
    _inboundPacketFlagQueue_ = None  #Note that this flag is set dynamically, so need to be careful about which instance is monitoring it.
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
        
        self._committedFlag_ = False #Indicates that the actionObject has been committed to the channel priority queue
        self._clearForReleaseFlag_ = threading.Event() #Indicates that the actionObject can be released from the channel priority queue and await transmission
        self._channelAccessGrantedFlag_ = threading.Event() #Indicates that the actionObject has been granted access to the channel in order to transmit
        
        self._channelAccessLock_ = None     #On channel access this will be set to the channel access lock object (provided by the interface) by _grantChannelAccess_
        
        self._inboundPacketFlag_ = threading.Event()
        
    def init(self, *args, **kwargs):    #user initialization routine. This should get overridden by the subclass.
        """actionObject subclass's initialization routine.
        
        This should be overridden by the user-defined subclass."""
        pass
    
    def setPacket(self, **kwargs):
        """Updates the dictionary that will be encoded by _outboundTemplate_ into an outgoing packet, using the provided keyword arguments.
        
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

    def commit(self):
        """Places this actionObject in its virtualNode interface's channel priority queue."""
        self._committedFlag_ = True     #record that actionObject has been committed
        self.virtualNode._interface_.commit(self)
        return True
 
    def _isCommitted_(self):
        """Returns committedFlag, indicating that this actionObject has been committed to the channel priority queue."""
        return self._committedFlag_
    
    def clearForRelease(self):
        """Flags the actionObject as clear to release from the channel priority queue.
        
        Note that the actual release procedure is performed by the channel priority thread.
        """
        self._clearForReleaseFlag_.set() #set the clear to release flag
        return True
    
    def _isClearForRelease_(self):
        """Returns True if the actionObject has been cleared for release from the channel priority queue."""
        return self._clearForReleaseFlag_.is_set()
    
    def _grantChannelAccess_(self, channelAccessLock = None):
        """Grants the actionObject access to its interface's transmission channel.
        
        channelAccessLock -- a threading.lock object that must be released by the actionObject when done using the channel.
        
        Note that if the lock object is not released, transmission will block on the interface indefinitely. The transmit function will automatically release
        the channel access lock unless explicitly directed not to.
        """
        self._channelAccessLock_ = channelAccessLock    #store a ref to the channel access lock
        self.onChannelAccess()  #call the user-defined onChannelAccess method
        self._channelAccessGrantedFlag_.set()   #set the channel access flag, to indicate to another thread that the actionObject has channel access
    
    def channelAccessIsGranted(self):
        """Returns True if the actionObject currently has interface channel access."""
        return self._channelAccessGrantedFlag_.is_set()
    
    def onChannelAccess(self):
        """User-overrridden optional method that gets called when the node receives channel access."""
        pass
        
    def waitForChannelAccess(self, timeout = None):
        """Blocks until the actionObject is granted channel access, or until timeout.
        
        timeout -- time in seconds to wait for channel access before admitting failure. A timeout of None means to wait indefinitely
        Returns True on channel access, and False on timeout.
        
        This function is most typically used from within an actionObject's init function to block the calling thread until having the opportunity to transmit
        and often receive.
        """
        if self._channelAccessGrantedFlag_.wait(timeout):
            return True     #access has been granted
        else:
            return False    #timeout
    
    def _releaseChannelAccessLock_(self):
        """Releases the actionObject's channel access lock."""
        if type(self._channelAccessLock_) != threading.Lock:    #check that channel access lock is the right type
            try:
                self._channelAccessLock_.release()  #attempt to release the lock
                return True
            except threading.ThreadError:   #channel access lock was already released
                notice(self, "Channel access lock was already released on call to _releaseChannelAccessLock_.")
                return False
        else:   #channel acess lock is not of type threading.Lock. How did it get there? Or why wasn't it set?
            notice(self, "actionObject has no valid channel access lock on call to _releaseChannelAccessLock_")
            notice(self, "Instead channel access lock type is " + str(type(self._channelAccessLock_)))
            return False
    
    @classmethod
    def _putActionObjectIntoInboundPacketFlagQueue_(cls, actionObject):
        """Swaps a provided actionObject into the inbound packet flag queue.
        
        actionObject -- the action object to be placed into the inbound packet flag queue.
        
        Note that although a queue is used, only one actionObject resided there at a time. Its occupant will be signaled when a packet is received.
        """
        cls._getActionObjectFromInboundPacketFlagQueue_()  #pulls any still-resident actionObject from the queue
        cls._inboundPacketFlagQueue_.put(actionObject) #put the provided actionObject into the queue
        return True
        
    @classmethod
    def _getActionObjectFromInboundPacketFlagQueue_(cls):
        """If avaliable, returns an actionObject from the inbound packet flag queue."""
        try:
            return cls._inboundPacketFlagQueue_.get(block=False)  #pulls an actionObject from the inboundPacketFlagQueue
        except:
            return False
    
    def transmit(self, mode = 'unicast', releaseChannelOnTransmit = True):
        """Transmits packet on the virtualNode's interface.
        
        mode -- the transmission mode, either 'unicast to direct at a single node, or 'multicast' to direct at all nodes.
        releaseChannelOnTransmit -- If True (default), will automatically release the actionObject's channel lock after transmission
        """
        
        if self.channelAccessIsGranted():   #very likely that transmit has been called from within an onChannelAccess function, since access is avaliable immediately
            self._putActionObjectIntoInboundPacketFlagQueue_(self)  #put a reference to self in the inbound packet flag queue
            self.virtualNode._interface_.transmit(actionObject = self, mode = mode)  #pass actionObject to interface for transmission
            if releaseChannelOnTransmit:  #check if should release the channel lock after transmission
                self._releaseChannelAccessLock_()  #release the channel access lock
            return True
        else:   #transmit was called before actionObject was granted channel access, take node thru to channel access
            if not self._isCommitted_():    #check if actionObject is already committed
                self.commit()   #commit actionObject to channel priority queue
            if not self._isClearForRelease_():   #check if actionObject is cleared for release from the channel priority queue
                self.clearForRelease()  #clear actionObject for release from the channel priority queue
            if self.waitForChannelAccess(): #wait for channel access
                self._putActionObjectIntoInboundPacketFlagQueue_(self)  #put a reference to self in the inbound packet flag queue
                self.virtualNode._interface_.transmit(actionObject = self, mode = mode) #transmit on interface
                if releaseChannelOnTransmit:    #check if should release the channel access lock
                    self._releaseChannelAccessLock_()   #release the channel access lock
            else:
                notice(self, "timed out waiting for channel access")    #timed out!
                return False
        return True        
    
    def transmitUntilResponse(self, timeout = 0.2, mode = 'unicast', attempts = 10):
        """Persistently transmits until a response is received from the node.
        
        timeout -- the time (in seconds) to wait for a reply between re-attempts
        mode -- the transmission mode, either 'unicast' to direct at a single node, or 'multicast' to direct at all nodes
        attempts -- the number of transmission attempts before giving up.
        
        This is an area in which to potentially improve Gestalt, by building in some functionality that
        can identify and respond intelligently to when a node goes down.
        """
        for thisAttempt in range(attempts): #make multiple attempts to receive a response
            self.transmit(mode = mode, releaseChannelOnTransmit = False)
            if self.waitForResponse(timeout):   #a response was received!
                self._releaseChannelAccessLock_()   #release access to the channel
                return True
            else:
                notice(self, "Could not reach virtual node. Retrying (#" + str(thisAttempt+2) + "/"+str(attempts)+")")
                continue
        #could not reach node if got to here
        self._releaseChannelAccessLock_()   #release access to the channel
        return False

    def waitForResponse(self, timeout = None):
        if self._inboundPacketFlag_.wait(timeout = timeout):    #inbound packet flag is set
            self._inboundPacketFlag_.clear()    #clear the flag
            return True     #return True to indicate that flag was set
        else:   #timeout has elapsed without flag being set
            return False

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
    
    def onReceive(self):
        """Default function to handle an asynchronously received inbound packet.
        
        This function will get called by the virtual node's _routeInboundPacket_ method. Note that very often this function will NOT be called in the same
        actionObject instance that transmitted, but rather a new actionObject that was instantiated by the virtual node's _routeInboundPacket_ method.
        """
        pass
    
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