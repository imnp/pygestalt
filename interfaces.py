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
        self._outboundAddressTable_ = {}    #{virtualNode:address} pairs
        self._inboundAddressTable_ = {}     #{address:virtualNode} pairs
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
        
        if address in self._outboundAddressTable_: 
            return True #address is already in use
        else:
            return False #address is not in use
