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
            
        