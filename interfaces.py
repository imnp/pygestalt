#   pyGestalt Interfaces Module

"""Provides interfaces for connecting virtual nodes with their physical counterparts."""


#---- INCLUDES ----
import threading
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
        pass
    
    class _channelAccessThread_(_interfaceThread_):
        pass
    
    class _receiveThread_(_interfaceThread_):
        pass

    class _packetRouterThread_(_interfaceThread_):
        pass
        