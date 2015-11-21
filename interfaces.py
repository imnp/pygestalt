#   pyGestalt Interfaces Module

"""Provides interfaces for connecting virtual nodes with their physical counterparts."""


#---- INCLUDES ----
import threading
import Queue
import time
import copy
import random   #for generating new addresses
from pygestalt import core, packets, utilities
from pygestalt.utilities import notice

class baseInterface(object):
    """The base class for all interfaces in the Gestalt framework."""
    pass

class gestaltInterface(baseInterface):
    """Communicates with physical nodes that have implemented the Gestalt protocol."""
    
    def __init__(self, name = None, interface = None, persistence = None):
        """Initialization function for the gestalt interface.
        
        name -- a user-provided name for the interface for use by utilities.notice.
        interface -- a downstream communications interface such as a serial port.
        persistence -- the persistence file that stores virtual/physical node associations
        """
        # Initialize Parameters
        self._name_ = name  #the interface's name for notification purposes
        self._interface_ = interface    #the downstream interface, e.g. a serial port
        self._persistence_ = persistence    #persistence file for storing virtual/physical node associations
        self._nodeAddressTable_ = {}    #{virtualNode:address} pairs for outbound transmissions
        self._addressNodeTable_ = {}     #{address:virtualNode} pairs for inbound transmissions
        self._shellNodeTable_ = {}          #maintains associations between virtual node shells and their contained nodes
        self._addressRangeMin_ = 1          #Reserve address 0.
        self._addressRangeMax_ = 65535      #maximum address value for gestalt nodes is 16-bit.
        self._threadIdleTime_ = 0.0005      #seconds, time for thread to idle between runs of loop
        
        self._gestaltPacket_ = packets.template('gestaltPacketTemplate',
                                              packets.unsignedInt('_startByte_',1), #start byte, 72 for unicast, 138 for multicast
                                              packets.unsignedInt('_address_',2),   #node address
                                              packets.unsignedInt('_port_',1),  #service routine port
                                              packets.length('_length_'),   #length of packet, determined automatically
                                              packets.packet('_payload_'), #included packet
                                              packets.checksum('_checksum_')) #automatically calculated checksum
        
        self._startInterfaceThreads_()  #start up interface threads 
        
    def _pullNewAddress_(self):
        """Generates a not-in-use address to be assigned to a new node.
        
        Note that any persistent addresses will have been loaded before this function has the opportunity to be called.
        """
        while True:     #Run until a unique address has been found
            testAddress = random.randint(self._addressRangeMin_, self._addressRangeMax_)  #randomly generate an address
            if not self._isAddressInUse_(testAddress):  #check if address is in use
                return testAddress  #address not in use, go ahead and return
    
    def _isAddressInUse_(self, address):
        """Checks whether an address is in use.
        
        address -- the address to be checked."""
        
        if address in self._addressNodeTable_: 
            return True #address is already in use
        else:
            return False #address is not in use

    def _replaceNode_(self, currentNode, newNode):
        """Replaces all references to oldNode with references to newNode while preserving the node address.
        
        currentNode -- the currently attached virtual node instance
        newNode -- the virtual node instance to replace the current node
        """
        address = self._nodeAddressTable_.pop(currentNode) #remove current node from node:address table
        self._updateNode_(newNode, address)   #updates the node address map
    
    def _updateNode_(self, virtualNode, address):
        """Updates entries in the node:address and address:node tables.
        
        virtualNode -- the virtual node to be updated
        address -- the address to be updated
        
        This function will most often be used to create new node-address mappings, but can also be used to simply update.
        """
        self._nodeAddressTable_.update({virtualNode:address})   #insert new node into node:address table
        self._addressNodeTable_.update({address:virtualNode})
        

    def attachNode(self, virtualNode):
        """Attaches a node to the Gestalt interface.
        
        virtualNode -- the node instance to attach to the interface
        
        Returns:
        newAddress -- the value of the new address, or False if no new address was necessary
        """
        if virtualNode._shell_ and (virtualNode._shell_ in self._shellNodeTable_):
            #The shell has already been affiliated with an attched node in the past, implying that the new attach request
            #is coming from an updated virtual node. So no new address should be pulled, just need to replace references
            #to the current node with references from the new node.
            oldVirtualNode = self._shellNodeTable_[virtualNode._shell_]
            self._replaceNode_(currentNode = oldVirtualNode, newNode = virtualNode) #replace node-address mapping
            newAddress = False
        else:
            #persistence check goes here. That'll be fun :-)
            newAddress = self._pullNewAddress_()
            self._updateNode_(virtualNode, newAddress)
            newAddress = self._nodeAddressTable_[virtualNode]
            
        self._shellNodeTable_.update({virtualNode._shell_:virtualNode}) #update shell node table
        
        return newAddress
    
    
    def _startInterfaceThreads_(self):
        """Starts the threads that monitor and operate the interface.
        
        The Gestalt interface is comprised of multiple threads that run simultaneously to handle the various transmission queues
        and also incoming packets. These threads are:
        channelPriorityThread - actionObjects waiting to be released into the channel access queue are monitored here.
        channelAccessThread - actionObjects waiting to transmit on the interface are monitored here.
        receiver - puts together incoming packets from bytes received on the interface
        packetRouter - once a packet has been fully received, this thread ... [NOTE: fill in details here]
        """
        self._channelPriority_ = self._startThreadAsDaemon_(self._channelPriorityThread_)
        self._channelAccess_ = self._startThreadAsDaemon_(self._channelAccessThread_)
        self._packetRouter_ = self._startThreadAsDaemon_(self._packetRouterThread_)
        self._receiver_ = self._startThreadAsDaemon_(self._receiveThread_)


    def _startThreadAsDaemon_(self, threadClass):
        """Creates an instance of the provided thread class and starts it as a daemon.
        
        threadClass -- the thread class to be instantiated
        
        Returns the running instance.
        
        Note that this function is designed to be used to start interface threads, and will thus automatically pass
        a self-reference to the thread's __init__.
        """
        threadInstance = threadClass(interface = self)  #create instance of thread
        threadInstance.daemon = True    #set thread instance as daemon, so that the python interpreter can end without needing to kill the thread first
        threadInstance.start()  #start the thread instance
        return threadInstance   #return the thread instance
        
        
    class _interfaceThread_(threading.Thread):
        """A base class for all interface threads.
        
        The only reason to make this custom base class is to accept and store a reference to the interface.
        """
        def __init__(self, interface):
            """Initializes thread and stores a reference to the interface."""
            threading.Thread.__init__(self)
            self.interface = interface
            self.init()
        
        def init(self):
            """Dummy init function to be overriden by derived class."""
            pass
    
    class _channelPriorityThread_(_interfaceThread_):
        """Manages actionObjects that are queued for release to the channel access thread.
        
        The first step in an actionObject's winding path towards transmitting its packet is the channel priority queue. While in this
        queue, actionObjects can still be modified, but the order in which they are queued cannot be changed. This permits features
        such as look-ahead motion planning, because attributes such as velocity and acceleration may change once future commands have
        been processed. Once an actionObject is released from the channel priority queue into the channel access queue, it can no
        longer be modified.
        """
        def init(self):
            """Initializes the channel priority thread."""
            self.channelPriorityQueue = Queue.Queue()   #create the channel priority queue
        
        def run(self):
            """The channel priority thread loop.
            
            This thread monitors the channel priority queue for a pending actionMolecule. Note that an actionMolecule can mean an object
            of type core.actionObject, but can also mean nested collections of actionObjects like sets and sequences. Once an actionMolecule
            has been cleared for release from the channel priority queue, it gets serialized into atomic actionObjects that are then released to the
            channel access queue. 
            """
            while True: #repeat forever
                pending, actionMolecule = self.getActionMolecule() #get the next actionObject (or actionSet, or actionSequence) from the queue.
                if pending: #an actionMolecule is waiting in the queue
                    while not actionMolecule._isClearForRelease_():    #wait for the actionMolecule to be cleared for release from the queue
                        time.sleep(self.interface._threadIdleTime_)  #idle
                    for actionObject in self.serializeActionMolecule(actionMolecule):   #serialize actionMolecule into actionObjects, and iterate over them
                        self.releaseActionObject(actionObject)  #put actionObject into the channel access queue
                else:
                    time.sleep(self.interface._threadIdleTime_) #idle
                
        def getActionMolecule(self):
            """Attempts to pull an actionMolecule from the channel priority queue.
            
            Returns (True, actionMolecule) if an actionMolecule was waiting in the queue, or (False, None) if not.
            """
            try:
                return True, self.channelPriorityQueue.get(block = False)    #signal success, return actionMolecule
            except Queue.Empty:
                return False, None  #signal failure, return None
        
        def putActionMolecule(self, actionMolecule):
            """Places actionMolecules into the channel priority queue.
            
            actionMolecule -- the actionMolecule to place into the queue.
            
            An actionMolecule is either simply an actionObject of type core.actionObject, or a collection of actionObjects in the 
            form of actionSets and actionSequences.
            """
            self.channelPriorityQueue.put(actionMolecule)
            return True
        
        def releaseActionObject(self, actionObject):
            """Releases an actionObject to the channel access queue.
            
            actionObject -- the actionObject to be released
            """
            self.interface._channelAccess_.putActionObject(actionObject)
            return True
        
        def serializeActionMolecule(self, actionMolecule):
            """Serializes an actionMolecule into a sequence of actionObjects.
            
            actionMolecules are comprised of various actionObject-containing structures to support multi-packet operations
            and synchronized packet execution. This function breaks apart these structures and serializes the contained
            actionObjects into the sequence in which they should be transmitted over the channel.
            """
            return [actionMolecule]   #for now nothing fancy, assume only actionObjects are used.
    
    def commit(self, actionMolecule):
        """Adds the provided actionMolecule to the channelPriorityQueue
        
        actionMolecule -- the actionMolecule to be added to the queue.
        """
        self._channelPriority_.putActionMolecule(actionMolecule)
    
    class _channelAccessThread_(_interfaceThread_):
        """Manages actionObjects that are waiting for access to the interface channel.
        
        Once an actionObject has been released from the channel priority queue, it sits in the channel access queue until
        its turn to gain access to the channel. 
        """
        def init(self):
            """Initialization routine for the channel access thread."""
            self.channelAccessQueue = Queue.Queue() #instantiate a queue for holding actionObjects awaiting channel access.
            self.channelAccessLock = threading.Lock()   #creates a lock object used to hand off access to an actionObject
            self.channelAccessLock.acquire()    #lock the lock object
        
        def run(self):
            """The channel access thread loop.
            
            Once an actionObject has been released into the channel access thread, it waits for the opportunity to access
            the channel. Upon access, the actionObject has complete control to send whatever it wants over the channel.
            This is slightly counter-intuitive at first, since it is the actionObject that controls the transmission
            rather than it occuring here. However this gives more flexibility to the designer of the actionObject.
            There are two primary patterns for how actionObjects will transmit. One is that they are blocking main program execution
            on their transmission, which makes sense for a function that e.g. needs a real-world sensor measurement in order to continue.
            The other pattern is that transmission occurs automatically on channel access while program execution occurs in parallel.
            Blocking behavior is supported by setting a flag triggering action in the main thread, and automatic transmission is 
            initiated by a call in this thread to the actionObject's grantAccess function.
            """
            while True:
                pending, actionObject = self.getActionObject()  #get the next action object from the queue
                if pending:
                    self.grantChannelAccess(actionObject)      #grant channel access to the actionObject
                    self.channelAccessLock.acquire()    #wait for actionObject to release the channel before continuing
                else:
                    time.sleep(self.interface._threadIdleTime_) #idle
        
        def getActionObject(self):
            """Attempts to pull an actionObject from the channel access queue.
            
            Returns (True, actionObject) if an actionObject was waiting in the queue, or (False, None) if not.
            """
            try:
                return True, self.channelAccessQueue.get(block = False)    #signal success, return actionMolecule
            except Queue.Empty:
                return False, None  #signal failure, return None            
            
        def putActionObject(self, actionObject):
            """Places actionObjects into the channel access queue.
            
            actionObject -- the actionObject to place into the queue.
            """
            self.channelAccessQueue.put(actionObject)
            return True
       
  
        def grantChannelAccess(self, actionObject):
            """Grants interface channel access to an actionObject.
                
            actionObject -- the action object which should be granted access.
            
            Granting channel access accomplishes three purposes:
            1) Notifies the actionObject that it has control of the channel.
            2) Transfers the channel access lock to the actionObject, who will release when done.
            3) Will run any immediate transmission routine in the current thread.
            """
            actionObject._grantChannelAccess_(self.channelAccessLock)    #grant channel access to the actionObject, and pass along the access lock                
    
    def _getVirtualNodeAddress_(self, virtualNode):
        """Returns the address of a provided virtual node.
        
        virtualNode -- the virtualNode instance whose address needs to be looked up.
        """
        if virtualNode in self._nodeAddressTable_:
            return self._nodeAddressTable_[virtualNode]
        else:
            return False
    
    def transmit(self, actionObject, mode):
        """Transmits a provided actionObject's packet over the interface.
        
        actionObject -- the actionObject making the call to transmit
        mode -- either 'unicast' or 'multicast'
        
        returns True if successful, or False if an error is encountered
        """
        port = actionObject.virtualNode.getPortNumber(actionObject)
        address = self._getVirtualNodeAddress_(actionObject.virtualNode)
        payload = actionObject._getEncodedOutboundPacket_()
        try:
            startByte = {'unicast':72, 'multicast':138}[mode]
        except:
            notice(self, "Transmission mode '" + str(mode) + "' is not valid.")
            return False
        packetEncodeDictionary = {'_startByte_':startByte, '_address_':address, '_port_':port, '_payload_':payload} #establish the encode dictionary
        encodedPacket = self._gestaltPacket_.encode(packetEncodeDictionary) #encode the complete outgoing packet
        
        #here is where a call to the downstream interface's transmit should get called
        #also need to work out how to do synthetic node calls here.
        
    class _receiveThread_(_interfaceThread_):
        pass

    class _packetRouterThread_(_interfaceThread_):
        pass
        