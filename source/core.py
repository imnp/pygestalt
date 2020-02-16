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
        
        Note that if a call is made to the actionObject before it is bound to a port, a notice will be issued and
        a None object will be returned.
        """
        if cls.virtualNode == None: #check to make sure the actionObject is bound
            notice(cls.__name__, "Can not instantiate actionObject because it isn't bound to a port on a virtual node!")   #not bound! give notice
            return None #not bound, return None
        
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
        self._channelAccessGrantedFlag_.set()   #set the channel access flag, to indicate to another thread that the actionObject has channel access
        self.onChannelAccess()  #call the user-defined onChannelAccess method    
        
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
    
    def releaseChannel(self):
        """Releases the communication channel.
        
        This method is typically called once the actionObject has finished transmitting multiple times. One example use-case is when loading a motion
        buffer that may be full at the time of initial transmission and requires a waiting period and then a re-attempt.
        
        Note that this is the user-accessible alias to _releaseChannelAccessLock_()
        """
        return self._releaseChannelAccessLock_()
    
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
    
    def transmitUntilResponse(self, timeout = 0.2, mode = 'unicast', attempts = 10, releaseChannelOnTransmit = True):
        """Persistently transmits until a response is received from the node.
        
        timeout -- the time (in seconds) to wait for a reply between re-attempts
        mode -- the transmission mode, either 'unicast' to direct at a single node, or 'multicast' to direct at all nodes
        attempts -- the number of transmission attempts before giving up.
        releaseChannelOnTransmit -- If True (default), will automatically release the actionObject's channel lock after transmission.
                                    It may be desirable to retain the channel lock if multiple transmissions are to be made.
        
        This is an area in which to potentially improve Gestalt, by building in some functionality that
        can identify and respond intelligently to when a node goes down.
        """
        for thisAttempt in range(attempts): #make multiple attempts to receive a response
            self.transmit(mode = mode, releaseChannelOnTransmit = False)
            if self.waitForResponse(timeout):   #a response was received!
                if releaseChannelOnTransmit: self._releaseChannelAccessLock_()   #release access to the channel
                return True
            else:
                if thisAttempt+1 < attempts:    #not the final attempt
                    notice(self, "Could not reach virtual node. Retrying (#" + str(thisAttempt+2) + "/"+str(attempts)+")")
                continue
        #could not reach node if got to here
        notice(self, "Unable to reach virtual node after " + str(attempts) + " attempts.")
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

#--- ACTION SEQUENCES ---
class actionSequence(object):
    pass

#--- SYNCHRONIZATION ---
class actionSet(object):
    """A set of actionMolecules that should be executed simultaneously, and synchronously, on the Gestalt network.
    
    Note: it is currently required that all contained actionObjects are on the same interface.
    """
    
    def __init__(self, *actionMolecules):
        """Initializes the actionSet.
        
        actionMolecules -- all objects provided positional arguments will be treated as members of the actionSet.
        """
        self.actionMolecules = list(actionMolecules)
    
    def __str__(self):
        return object.__str__(self) + " CONTAINING: " + str([actionMolecule for actionMolecule in self.actionMolecules])


class syncToken(object):
    """A token object used to synchronize multiple nodes on a network."""
    pass

def distributedFunctionCall(owner, targetList, attribute, syncTokenType, *arguments, **keywordArguments):
    """Distributes a function call across a list of target objects.
    
    owner -- A reference to the initiating object. This is used for providing notices.
    targetList -- a list of target objects across which the function call will be distributed
    attribute -- the attribute name that should be called
    syncTokenType -- A reference to a token class that should be used for synchronization IN THE EVENT THAT THERE ARE UNIQUELY
                     DISTRIBUTED ARGUMENTS, or False or None if no synchronization tokens are to be injected.
    arguments -- positional arguments to be forwarded on to the targets. Any tuples will be uniquely distributed based on
            the position in the tuple. Other types will be evenly distributed to all targets
    keywordArguments -- keyword arguments to be forwarded on to the targets. Same distribution rules as for positional arguments.
    
    This function will make a function call at the provided attribute on all objects in the provided target list. If any of
    the positional arguments in args, or the keyword arguments in kwargs, are provided as a tuple, these arguments will be uniquely
    distributed to all objects in targetList. For example, distributedFunctionCall(callOwner, [obj1, obj2], funcName, (1,2), myArg = 3)
    would be result in calls obj1.funcName(1, myArg = 3) and obj1.funcName(2, myArg = 3).
    
    Note that the common use is for a reference to this function to be passed as part of a functools.partial object. While this function
    may serve other purposes, it is primarily intended to be used in the context of compound nodes.
    
    In the event that uniquely distributed arguments exist, we assume that the function call should be synchronized across the
    targets. In order to accomplish this, a synchronization token type can be passed to this method. An instance of this token will
    be generated and injected into the kwargs of the distributed function calls with the key 'sync'. To prevent this behavior,
    None or False can be provided to this method instead.
    
    If no syncTokenType is provided, there are no uniquely distributed arguments, or the returned types are not either actionObjects or
    actionSequences, return values for each of these calls will be simply returned as a concatenated tuple. If a syncTokenType IS provided, 
    AND if there ARE uniquely distributed arguments, AND all returned types are either an actionObject or an actionSequence, an actionSet
    will be returned.
    
    If an error occurs, returns False instead.
    """
    
    #-- Initialization --
    targetCount = len(targetList) #total number of target objects
    expandedArguments = [] #stores positional arguments as [[arg1_target1, arg1_target2, ...], [arg2_target1, arg2_target2]]
    expandedKeywordArguments = [] #stores keyword arguments as [[{arg1_target1},{arg1_target2}],[{arg2_target1},{arg2_target2}]]
    uniqueDistribution = False #starts as False, but set to True should any arguments require unique distribution
    
    #-- Organize Positional Arguments --
    for argument in arguments: #iterate over all provided positional arguments
        if type(argument) == tuple: #uniquely distributed argument
            uniqueDistribution = True #flag that unique distribution is required
            if len(argument) == targetCount: #there are the correct number of provided arguments
                expandedArguments += [list(argument)] #simply convert tuples to a list
            else: #incorrect number of arguments provided!
                notice(owner, attribute + ': incorrect number of arguments provided!')
                return False
        else: #evenly distributed argument
            expandedArguments += [[argument for target in targetList]]
    
    collectedArguments = zip(*tuple(expandedArguments)) #a list of tuples: [(arg1_target1, arg2_target1), (arg1_target2, arg2_target2)]
    
    #-- Organize Keyword Arguments --
    for key, value in keywordArguments.iteritems(): #iterate over all provided keyword arguments
        if type(value) == tuple: #uniquely distributed argument
            uniqueDistribution = True
            if len(value) == targetCount: #there are the correct number of provided arguments
                expandedKeywordArguments += [[{key:thisValue} for thisValue in value]]
            else: #incorrect number of arguments provided
                notice(owner, attribute + ': incorrect number of arguments provided for keyword argument "' + key +'"!')
                return False
        else: #evenly distributed argument
            expandedKeywordArguments += [[{key:value} for target in targetList]]
    
    zippedKeywordArguments = zip(*tuple(expandedKeywordArguments)) # a list of tuples: [({arg1_target1},{arg2_target1}), ({arg1_target2}, arg2_target2})]
    collectedKeywordArguments = [{key:value for pair in thisTuple for key, value in pair.items()} for thisTuple in zippedKeywordArguments]
        # The above results in [{arg1_target1, arg2_target1}, {arg1_target2, arg2_target2}]
    
    #-- Synchronization --
    if uniqueDistribution and syncTokenType: #unique distribution has occured, and syncronization is enabled
        syncToken = syncTokenType() #generate a new syncronization token
        for keywordDictionary in collectedKeywordArguments: keywordDictionary.update({'sync':syncToken}) #updates all kwarg dictionaries
    
    #-- Function Calls --
    returnTuple = tuple([callFunctionWithChecking(owner, target, attribute, *args, **kwargs) for target, args, kwargs in zip(targetList, collectedArguments, collectedKeywordArguments)])
    
    #-- Return Values --
    allAreActionMolecules = all([(type(element) == actionObject or type(element) == actionSequence) for element in returnTuple]) #True if all elements are action molecules (i.e. actionObjects or actionSequences)
    
    if uniqueDistribution and syncTokenType and allAreActionMolecules: #return as an actionSet
        return actionSet(*returnTuple)
    else:
        return returnTuple
    
    
def callFunctionWithChecking(owner, target, attribute, *args, **kwargs):
    """Calls a function on a target with a provided set of positional and keyword arguments.
    
    owner -- A reference to the initiating object. Used for providing notices.
    target -- the target object
    attribute -- the name of the method to be called
    args -- positional arguments
    kwargs -- keyword arguments
    
    The purpose of wrapping the function call like this is to provide feedback if the attribute doesn't exist.
    
    Returns the result of the function call.
    """
    if hasattr(target, attribute):
        return getattr(target, attribute)(*args, **kwargs)
    else:
        notice(owner, type(target).__name__.upper() + " DOESN'T HAVE THE REQUESTED ATTRIBUTE '" + attribute + "'.")
        raise AttributeError(attribute)
