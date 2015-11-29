#   pyGestalt Interfaces Module

"""Provides interfaces for connecting virtual nodes with their physical counterparts."""


#---- INCLUDES ----
import threading
import Queue
import time
import copy
import random   #for generating new addresses
import serial
from pygestalt import core, packets, utilities, config
from pygestalt.utilities import notice

class baseInterface(object):
    """The base class for all interfaces in the Gestalt framework."""
    pass

class serialInterface(baseInterface):
    """The base class for all serial port interfaces."""
    
    def __init__(self, portName = None, baudRate = 115200, interfaceType = None, name = None, timeout = 0.1, flowControl = None):
        """Initializes a serial communications port.
        
        portName -- the system name of the port, e.g. 'tty.usbserial*' on a Mac, or 'COM0' on Windows
        baudRate -- the communications speed to be used. Default is 115200 baud.
        interfaceType -- a string keyword to help search for the port. Types include 'ftdi' 
        name -- an optional name to provide to the interface
        timeout -- receiver timeout in seconds before returning '' if no data has been received
        flowControl -- TBD, can be used to enable hardware flow control, or to bring an Arduino into reset, once implemented.
        """
    
        self.providedPortName = portName    #the name of the port provided on instantiation
        self.portName = portName    #the name of the port last connected to. This can be automatically changed by the connect method
        self.baudRate = baudRate
        self.interfaceType = interfaceType
        self._name_ = name
        self.timeout = timeout
        self.flowControl = flowControl
        
        self.port = None    #the currently connected port
        self.isConnectedFlag = threading.Event()    #keeps track of current status of interface
        self._threadIdleTime_ = 0.0005  #seconds, time for thread to idle between runs of loop
        self._portReconnectTime_ = 5    #seconds, time between attempts to reconnect to a down port.
        self.connect()
        self.transmitter = self.startTransmitter()
    
    def connect(self, portName = None):
        """Connect to a serial port.
        
        portName -- the full name of the serial port to which to connect. If None, will attempt to connect to self.portName.
        
        This function will attempt to connect to either the provided port name, or the interface's self.portName. If a port is provided
        as the input argument, and if connection is successful, self.portName will be updated to reflect the currently connected port.
        
        If synthetic mode is enabled globally (in pygestalt.config) this method will not attempt to connect and will return False.
        """
        if portName:
            connectToPortName = portName    #use argument if provided
        elif self.portName:
            connectToPortName = self.portName   #default to interface's portName
        else:
            connectToPortName = None
            
        if not config.syntheticMode():  #not in global synthetic mode
            try:
                self.port = serial.Serial(connectToPortName, self.baudRate, timeout = self.timeout) #Connect to the serial port
                self.port.flushInput()  #do some spring cleaning
                self.port.flushOutput()
                time.sleep(2)   #some ports require a brief amount of time between opening and transmission
                self.isConnectedFlag.set() #sets the is connected flag
                self.startTransmitter() #starts up the transmission thread
                notice(self, "Successfully connected to port " + str(connectToPortName))    #brag a little bit
                return True
            except StandardError, error:
                notice(self, "Error opening serial port " + str(connectToPortName))
                notice(self, error) #report system-provided error.
                return False
        else:   #in global synthetic mode, don't connect and return False
            return False
    
    def isConnected(self):
        """Returns True if the isConnectedFlag is set, otherwise False."""
        return self.isConnectedFlag.is_set()
    
    def transmit(self, packet):
        """Transmits a packet over the serial interface.
        
        packet -- the packets.serializedPacket to be transmitted
        """
        if self.isConnected():  #check to make sure connected before transmitting
            self.transmitter.putPacketInTransmitQueue(packet)    #put data packet into the transmission queue
            return True
        else:
            notice(self, str(self.portName)+ " is not connected!")
            return False
    
    def receive(self):
        """Reads one byte from the serial port input buffer.
        
        Note that if a port is open, this function will block while waiting for a byte. If the serialInterface is the interface for a
        gestaltInterface, there is a receive thread that doesn't mind blocking.
        """
        if self.isConnected():
            try:
                return self.port.read(size = 1) #reads a single byte from the serial port. If empty will wait timeout period established on port instantiation, then returns ''
            except: #likely that port closed while waiting to receive
                notice(self.interface, "Lost connection to serial port " + str(self.interface.portName))
                self.isConnectedFlag.clear()    #mark that port is closed. It will need to be reopened by the transmit thread.
                return None
        else:
            return None
    
    def startTransmitter(self):
        """Starts up the transmitter thread.
        
        Returns the transmitter thread instance.
        """
        transmitter = self.transmitterThread(self)    #instantiate a transmitter thread
        transmitter.daemon = True  #make transmitter thread a daemon so exits when program ends
        transmitter.start()    #start up the transmitter!
        return transmitter
    
    class transmitterThread(threading.Thread):
        """This thread handles transmitting bytes over a serial port."""
        def __init__(self, interface):
            """Initializes the transmitter thread.
            
            interface -- a reference to the serialInterface instance in the context of which this thread runs.
            """
            threading.Thread.__init__(self) #initialize threading parent class
            self.interface = interface  #a reference to serialInterface instance
            self.transmitQueue = Queue.Queue()  #Use a queue to permit background transmission, and to allow multiple threads to access the interface.
        
        def run(self):
            """Transmitter thread loop.
            
            New in this version of Gestalt, the thread attempts to reconnect to a port if connection is lost.
            """
            while True:
                if self.interface.isConnected():    #check to make sure that the interface is connected
                    pending, packet = self.getPacketFromTransmitQueue() #try to get packet from the queue
                    if pending:
                        try:
                            self.interface.port.write(packet.toString())
                        except: #IF THIS EXCEPTS, MIGHT WANT TO ADD A WAY TO RETRANSMIT THE PACKET. GETS HAIRY.
                            self.interface.port.isConnectedFlag.clear() #port is no longer connected
                            notice(self.interface, "Lost connection to serial port " + str(self.interface.portName))
                        time.sleep(self.interface._threadIdleTime_) #idle
                else:   #port isn't connected, attempt to reconnect
                    time.sleep(self.interface._portReconnectTime_)
                    self.interface.connect()    #attempt to reconnect         
        
        def getPacketFromTransmitQueue(self):
            """Attempts to pull a packet from the transmit queue.
            
            Returns (True, packet) if data is waiting in the queue to be transmitted, or (False, None) if not.
            """
            try:
                return True, self.transmitQueue.get(block = False)    #signal success, return packet
            except Queue.Empty:
                return False, None  #signal failure, return None  
        
        def putPacketInTransmitQueue(self, packet):
            """Puts a packet in the transmit queue.
            
            packet -- a packet of type packets.serializedPacket
            """
            if type(packet) == packets.serializedPacket:
                self.transmitQueue.put(packet)
                return False
            else:
                notice(self.interface, "Can only place packets.serializedPacket objects in the transmitter queue. Instead received type "+ str(type(packet)))
                return False      
        
        
        
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
        self._syntheticResponse_ = self._startThreadAsDaemon_(self._syntheticResponseThread_)
        self._receiver_ = self._startThreadAsDaemon_(self._receiveThread_)
        self._packetRouter_ = self._startThreadAsDaemon_(self._packetRouterThread_)


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
                return True, self.channelAccessQueue.get(block = False)    #signal success, return actionObject
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
    
    def _getAddressOfVirtualNode_(self, virtualNode):
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
        port = actionObject.virtualNode._getPortNumber_(actionObject)
        address = self._getAddressOfVirtualNode_(actionObject.virtualNode)
        payload = actionObject._getEncodedOutboundPacket_()
        try:
            startByte = {'unicast':72, 'multicast':138}[mode]
        except:
            notice(self, "Transmission mode '" + str(mode) + "' is not valid.")
            return False
        packetEncodeDictionary = {'_startByte_':startByte, '_address_':address, '_port_':port, '_payload_':payload} #establish the encode dictionary
        encodedPacket = self._gestaltPacket_.encode(packetEncodeDictionary) #encode the complete outgoing packet
        
        if actionObject.virtualNode._isInSyntheticMode_():   #return a synthetic response
            return self._syntheticResponse_.putInSyntheticQueue(encodedPacket = encodedPacket, syntheticResponseFunction = actionObject._synthetic_)
        else:   #not running in synthetic mode, so pass along the packet to the transmitter
            return self._interface_.transmit(encodedPacket)
            
        
    class _syntheticResponseThread_(_interfaceThread_):
        """Generates synthetic inbound packets to simulate responses from physical nodes for development purposes.
        
        The purpose of this thread is to simulate the communications behavior of a physical node combined with the receiver thread.
        This is accomplished by the following process:
        1) A tuple of format (encodedOutboundPacket, syntheticResponseFunction) is placed into the synthetic response queue by the putInSyntheticQueue method.
        2) The encodedOutboundPacket will be decoded here to retrieve the outbound payload
        3) This thread will call syntheticResponseFunction - typically the _synthetic_ method of an actionObject - with the outbound payload as an argument.
        4) syntheticResponseFunction will return an encoded response payload.
        5) The response payload is placed back in the decoded outbound packet dictionary, which is then passed along to the packet router thread as if it had
            just been received. NOTE: as currently implemented, synthetic responses can only be directed at the same node and calling port from which the
            outbound packet originated.
        """
        def init(self):
            """Synthetic node thread initialization method."""
            self.syntheticResponseQueue = Queue.Queue()
        
        def run(self):
            """Synthetic response thread loop."""
            while True:
                pending, syntheticTuple = self.getSyntheticTuple()  #get from the queue the next tuple containing information to generate a synthetic packet
                if pending: #a tuple was waiting
                    #TODO: handle multicast packets
                    encodedOutboundPacket, syntheticResponseFunction = syntheticTuple   #break apart stored tuple
                    decodedOutboundPacket = self.interface._gestaltPacket_.decode(encodedOutboundPacket)[0]    #decode the outgoing packet
                    outboundPayload = decodedOutboundPacket['_payload_']  #get the outbound payload from the decoded outbound packet
                    syntheticInboundPayload = syntheticResponseFunction(outboundPayload) #generate an encoded inbound payload
                    if syntheticInboundPayload != None: #a synthetic payload was provided by the node
                        decodedSyntheticInboundPacket = copy.copy(decodedOutboundPacket)    #make a copy of the decoded outbound packet to use as an inbound packet
                        decodedSyntheticInboundPacket.update({'_payload_':syntheticInboundPayload}) #swap the outbound payload for the new synthetized payload
                        self.interface._packetRouter_.putDecodedPacket(decodedSyntheticInboundPacket)   #put the decoded inbound packet into the packet router queue
                else:
                    time.sleep(self.interface._threadIdleTime_) #idle

        def getSyntheticTuple(self):
            """Attempts to pull a tuple from the synthetic response queue.
            
            Returns (True, tuple) if a tuple was waiting in the queue, or (False, None) if not.
            """
            try:
                return True, self.syntheticResponseQueue.get(block = False)    #signal success, return tuple
            except Queue.Empty:
                return False, None  #signal failure, return None            
            
        def putInSyntheticQueue(self, encodedPacket, syntheticResponseFunction):
            """Places objects into the synthetic response queue.
            
            encodedPacket -- a fully encoded packet just as it would be transmitted
            syntheticResponseFunction -- the function that will be used to generate a synthetic response, typically of type actionObject._synthetic_
            """
            self.syntheticResponseQueue.put((encodedPacket, syntheticResponseFunction))
            return True
                 
    
    class _receiveThread_(_interfaceThread_):
        """Receives a incoming packet over the interface channel and when complete places the packet in the packet router queue."""
        
        def resetReceiverState(self):
            self.inProcessPacket = []    #initialize the currently received packet
            self.packetReceiveState = 'waitingOnStartByte'
            self.packetLength = 0
        
        def validateAndDecodeInProcessPacket(self):
            """Validates and decodes self.inProcessPacket.
            
            returns the decoded packet in dictionary format if successful, or False if validation or decoding were unsuccessful
            """
            packet = packets.serializedPacket(self.inProcessPacket)   #convert to a packets.serializedPacket object
            if self.interface._gestaltPacket_.validateChecksum('_checksum_', packet): #checksum validates
                decodedPacket = self.interface._gestaltPacket_.decode(packet)[0]
                return decodedPacket
            else:
                return False
            
            
        def run(self):
            """Main receiver loop."""
            
            self.resetReceiverState()   #reset the receiver state
            decodeIncompletePacket = self.interface._gestaltPacket_.decodeTokenInIncompletePacket #just a convenient alias to the gestalt packet's decodeIncompletePacket method
            
            while True:
                if self.interface._interface_:  #a downstream interface exists
                    receivedCharacter = self.interface._interface_.receive()    #will attempt to read in one character, but will return '' if nothing is avaliable after timeout period, or port is disconnected
                else:
                    time.sleep(self.interface._threadIdleTime_) #idle
                    continue                    
                if receivedCharacter:    #character was received
                    receivedByte = ord(receivedCharacter)   #convert to an integer byte
                    self.inProcessPacket += [receivedByte]
                    if self.packetReceiveState == 'waitingOnStartByte': #waiting on the start byte
                        success, startByte = decodeIncompletePacket('_startByte_', self.inProcessPacket)
                        if success: #could successfully decode start byte
                            if (startByte == 72 or startByte == 138):   #start byte is valid
                                self.packetReceiveState = 'waitingOnLengthByte'   #put receiver in next state: wait for address to be received
                                continue
                            else:
                                self.resetReceiverState() #reset the receiver state, and begin listening again
                                continue
                        else:   #haven't received the _startByte_ yet. In case for some reason _startByte_ ever becomes a two-byte word. Leaving this interpretation up to the packet.
                            continue
                        
                    elif self.packetReceiveState == 'waitingOnLengthByte': #waiting on the length
                        success, length = decodeIncompletePacket('_length_', self.inProcessPacket)
                        if success:
                            self.packetReceiveState = 'waitingToFinish'
                            self.packetLength = length + 1  #checksum byte is not included in the figure reported by the length token.
                        continue
                    
                    elif self.packetReceiveState == 'waitingToFinish':
                        if len(self.inProcessPacket) == self.packetLength:  #entire packet has been received
                            decodedPacket = self.validateAndDecodeInProcessPacket()
                            if decodedPacket: #packet validates against checksum
                                self.interface._packetRouter_.putDecodedPacket(decodedPacket)    #convert to packets.serializedPacket type and put the decoded packet in the router queue
                                self.resetReceiverState()   #reset the receiver state
                                continue
                            else:   #packet didn't validate, reset the receiver and continue
                                self.resetReceiverState()
                                continue
                        else:   #haven't reached the end of the packet yet
                            continue
                else:   #receiver timed out, reset state
                    self.resetReceiverState()
                    time.sleep(self.interface._threadIdleTime_) #idle
                            
                        
    def _getVirtualNodeFromAddress_(self, address):
        """Returns the virtual node whose address matches a provided value.
        
        address -- the virtual node address to be looked up.
        """
        if address in self._addressNodeTable_:  #check that a virtual node matches the provided address
            return self._addressNodeTable_[address] #returns the matching node
        else:
            return False    #address does not map to a node, return False
        

    class _packetRouterThread_(_interfaceThread_):
        """Routes incoming packets to their destination virtual node.
        
        When a packet has been successfully received, it is transfered to the packet router thread to be routed to a destination node.
        The node will then instantiate an actionObject according to its port binding table and call its onReceive method, and will also set an inboundPacketFlag on the
        destination actionObject class. The onReceive method is called in the packet router thread, whereas the inboundPacketFlag may be read and acted upon by a
        different thread.
        """
        def init(self):
            """Packet router thread initialization method."""
            self.routerQueue = Queue.Queue()    #create a packet router queue.
        
        def run(self):
            """Packet router loop.
            
            Note that inbound packets are pulled from the queue already decoded (this was done in the receive thread to validate the checksum).
            """
            while True:
                pending, decodedPacket = self.getDecodedPacket()  #get the next decoded packet from the queue
                if pending: #a packet was waiting
                    destinationAddress = decodedPacket['_address_']
                    destinationPort = decodedPacket['_port_']
                    payload = decodedPacket['_payload_']
                    virtualNode = self.interface._getVirtualNodeFromAddress_(destinationAddress)    #look up virtual node that matches the packet's address
                    virtualNode._routeInboundPacket_(port = destinationPort, packet = payload) #call the virtual node's packet router method
                else:
                    time.sleep(self.interface._threadIdleTime_) #idle

        def putDecodedPacket(self, decodedPacket):
            """Places decoded packet dictionaries into the router queue.
            
            decodedPacket -- the decoded packet dictionary to place into the queue.
            """
            self.routerQueue.put(decodedPacket)
            return True
                    
        def getDecodedPacket(self):
            """Attempts to pull a decoded packet dictionary from the router queue.
            
            Returns (True, decodedPacket) if a decoded packet dictionary was waiting in the queue, or (False, None) if not.
            """
            try:
                return True, self.routerQueue.get(block = False)    #signal success, return decoded packet
            except Queue.Empty:
                return False, None  #signal failure, return None  