#   pyGestalt Nodes Module

"""A standard set of base node classes."""


#---- INCLUDES ----
import threading
import time
import imp, os, urllib  #for importing files
import copy
from pygestalt import core, packets
from pygestalt.utilities import notice

class baseVirtualNode(object):
    """Base class for all virtual nodes"""
    
    def __init__(self, *args, **kwargs):
        """Default initializer for all virtual nodes.
        
        This should be overridden.
        """

    def _recursiveInit_(self, recursionDepth, *args, **kwargs):
        """Dummy initializer function."""
        pass
    
    def _recursiveInitLast_(self, recursionDepth):
        """Dummy final initialization function."""
        pass
    
    def _recursiveOnLoad_(self, recursionDepth):
        """Dummy onLoad function.
        
        This is where the recursion terminates"""
        pass

class baseGestaltNode(baseVirtualNode):
    """Base class for Gestalt nodes."""

    def __init__(self, *args, **kwargs):
        """Initializes Gestalt Node.
        
        Initialization occurs by calling a sequence of specialized initialization functions. In order to
        support inheritance, and to make sure that all of the inherited functions are called, the parent
        class initialization functions must be called recursively. This function is the entry point into
        the process and starts at a recursion depth of 0.
        
        PARAMETERS PULLED FROM KEYWORD ARGUMENTS (and not passed along to child classes):
        name -- the name of the node
        interface -- the interface to use for communication
        _shell_ -- if the node is set within a shell, the shell object passes along a self-reference here
        """
        
        self._outboundPortTable_ = {}   #stores function:port pairs as assigned by bindPort
        self._inboundPortTable_ = {} #stores port:function pairs as assigned by bindPort
        
        #-- Parse Optional Initialization Parameters --
        originalArgs = copy.copy(args)  #store original arguments for _updateVirtualNode_
        originalKwargs = copy.copy(kwargs)
        
        if "name" in kwargs:
            self._name_ = kwargs.pop("name")    #pop name from named arguments, and set as node name. This is used by utilities.notice and for persistence.
        else:
            self._name_ = None  #default value
            
        if "interface" in kwargs:
            self._interface_ = kwargs.pop("interface")      #the interface on which the node will communicate
        else:
            self._interface_ = None
        
        if "_shell_" in kwargs:
            self._shell_ = kwargs.pop("_shell_")
        else:
            self._shell_ = None
            
        #-- Initialization--
        self._recursiveInit_(0, *args, **kwargs) #begin recursive initialization at a depth of 0.
        self._recursiveInitLast_(0) #begin recursive initLast
        self._initInterface_() #Initializes node into a gestalt interface
        if not self._updateVirtualNode_(originalArgs, originalKwargs):  #Updates the virtual node object contained within _shell_ based on URL received from node
            self._recursiveOnLoad_(0)   #begin recursive onLoad if virtual node instance still valid after _updateVirtualNode_
        else: #returned True: this virtual node instance has been supplanted
            pass    #last instruction that will be called on this particular virtual node instance
            
            
    def _recursiveInit_(self, recursionDepth, *args, **kwargs):
        """Recursively initializes Gestalt node.
        
        THIS FUNCTION IS ONLY CALLED INTERNALLY BY __init__
        Initialization occurs in the following steps:
        1) parent class initialization: a call to parentClass._recursiveInit_
        2) init: user initialization routine for defining optional constants etc. that are specific to the node
        3) packets: packet templates are defined here
        4) ports: actionObjects and packets are bound to ports
        
        The following final steps are done in individual recursive batches, so each will run on all subclasses before the next is called.
        5) last: any actions that must be performed after all subclasses have had a chance to initialize, like setting the node into the interface.
        --- node is bound to interface here ---
        6) onLoad: anything that needs to get initialized with the ability to communicate to the node.
        """
        baseClass = self.__class__.mro()[recursionDepth] #base class is determined by the method resolution order indexed by the recursion depth.
        parentClass = self.__class__.mro()[recursionDepth + 1] #parent class is determined the same way
        parentClass._recursiveInit_(self, recursionDepth + 1, *args, **kwargs) #recursively initialize using parent class
        if 'init' in baseClass.__dict__: baseClass.init(self, *args, **kwargs) #run user initialization routine with provided arguments
        if 'initPackets' in baseClass.__dict__: baseClass.initPackets(self) #initialize packets
        if 'initPorts' in baseClass.__dict__: baseClass.initPorts(self) #initialize ports
    
    def _recursiveInitLast_(self, recursionDepth):
        """Recursively calls initLast routine across parent virtual node classes.
        
        THIS FUNCTION IS ONLY CALLED INTERNALLY BY __init__, after calling _recursiveInit_
        """
        baseClass = self.__class__.mro()[recursionDepth] #base class is determined by the method resolution order indexed by the recursion depth.
        parentClass = self.__class__.mro()[recursionDepth + 1] #parent class is determined the same way
        parentClass._recursiveInitLast_(self, recursionDepth + 1) #recursively calls onLoad using parent class        
        if 'initLast' in baseClass.__dict__: baseClass.initLast(self) #run after initialization is complete        
    
    def _recursiveOnLoad_(self, recursionDepth):
        """Recursively calls onLoad routine across parent virtual node classes.
        
        THIS FUNCTION IS ONLY CALLED INTERNALLY BY __init__, after calling _recursiveInitLast_
        """
        baseClass = self.__class__.mro()[recursionDepth] #base class is determined by the method resolution order indexed by the recursion depth.
        parentClass = self.__class__.mro()[recursionDepth + 1] #parent class is determined the same way
        parentClass._recursiveOnLoad_(self, recursionDepth + 1) #recursively calls onLoad using parent class        
        if 'onLoad' in baseClass.__dict__: baseClass.onLoad(self) #run after initialization is complete
    
    def init(self, *args, **kwargs):
        """User initialization routine for defining optional constants etc. that are specific to the node hardware.
        
        Examples of this might be the crystal frequency, or an ADC reference voltage.
        """
        pass
    
    def initPackets(self):
        """Initializes packet templates."""
        pass
    
    def initPorts(self):
        """Bind actionObjects and packets to ports."""
        pass
    
    def initLast(self):
        """Runs any initialization functions that must be performed after all node subclasses classes have undergone standard initialization steps."""
        pass
    
    def onLoad(self):
        """Run any initialization functions that must communicate with the physical node.
        
        An example might be setting some default parameters on the node.
        """
        pass
    
    def _initInterface_(self):
        """Initializes the node in the context of an interface by which it will communicate with the outside world."""
        pass

    def _updateVirtualNode_(self, args = (), kwargs = {}):
        """Attempts to replace virtual node instance residing inside _shell_ (e.g. self) with an updated version as referenced by the physical node's URL.
        
        This is perhaps one of the weirder initialiation steps of the Gestalt node. As has been discussed previously, when a virtual node is first initialized and
        before it has communicated with its physical node, a default base class (nodes.gestaltNode) is used. The base class contains just the functionality
        to retreive a URL from the physical node that points to a feature-complete virtual node matching the physical node. _updateVirtualNode_ handles
        retrieving the URL and attempting to instantiate a new virtual node using the referenced file. If successful, this function will replace the base
        virtual node with the retrieved version. All of this is predicated on the node having been instantiated within a shell, and without a source being
        explicitly provided. If no shell is provided it is assumed that the feature-complete virtual node has been directly imported. Keep in mind that the
        present function is part of the base class and will run multiple times.
        
        Returns True if the node has successfully been replaced, or False if not.
        """ 
        #run some basic checks first
        if self._shell_ == None:    #no shell has been provided
            return False

        if self._shell_._nodeLoaded_:   #a non-default node is already loaded into the shell.
            return False
        
        nodeStatus, appValid = self.statusRequest() #get current status of node
        
        if not appValid:    #application is not valid
            notice(self, "Application firmware is invalid!")
            return False
        
        if nodeStatus == 'B':   #in bootloader mode, attempt to switch to application mode
            if not self.runApplication():   #cannot switch to application mode
                notice(self, "Unable to switch node to application mode.")
                notice(self, "Running in bootloader mode!")
                return False

        nodeURL = self.urlRequest() #get node URL
        
        self._shell_._loadNodeFromURL_(nodeURL, args, kwargs)


    def bindPort(self, port, outboundFunction = None, outboundTemplate = None, inboundFunction = None, inboundTemplate = None ):
        """Attaches actionObject classes and templates to a communication port, and initializes relevant parameters.
        
        port -- a port number ranging from 1 to 254
        outboundFunction -- an actionObject class that will transmit on the specified port
        outboundTemplate -- the packet template that should be used to encode any packets sent on the specified port
        inboundFunction -- an actionObject class taht will receive on the specified port
        inboundTemplate -- the packet template that should be used to decode any packets sent on the specified port
        
        If either inbound or outbound functions are not provided, these will be automatically generated.
        
        Note that the parameter names contain the reference "function" strictly for the benefit of the user, since in practice they behave like functions.
        """
        
        inboundPacketFlag = threading.Event()    #This flag will be used to signal to an outbound function that a reply has been received.
        
        #GENERATE actionObject CLASSES
        if outboundFunction != None:    #an outbound function has been provided
            outboundActionObjectClass = self.addDerivedType(outboundFunction)   #this is the class that will actually get called to instantiate action objects
                                                                                #during use. It is a derived class of the provided outboundFunction class. 
            outboundActionObjectClass._baseActionObject_ = outboundFunction            #store the base class for introspection use later
        else: #no outbound function has been provided, must generate one.
            typeName = "outboundActionObjectOnPort"+ str(port)    #make up a name that is unique
            outboundActionObjectClass = self.addDerivedType(core.genericOutboundActionObjectBlockOnReply, typeName)
            outboundActionObjectClass._baseActionObject_ = core.genericOutboundActionObjectBlockOnReply
        
        if inboundFunction != None: #an inbound function has been provided
            inboundActionObjectClass = self.addDerivedType(inboundFunction)
            inboundActionObjectClass._baseActionObject_ = inboundFunction
        else: #no inbound function has been provided, must generate one
            typeName = "inboundActionObjectOnPort" + str(port)    #make up a name that is unique
            inboundActionObjectClass = self.addDerivedType(core.genericInboundActionObject, typeName)
            inboundActionObjectClass._baseActionObject_ = inboundFunction
        
        #GENERATE MISSING PACKET TEMPLATES
        if outboundTemplate == None:
            templateName = 'outboundTemplateOnPort' + str(port)
            outboundTemplate = packets.emptyTemplate(templateName)  #must use an emptyTemplate type because template cannot have an empty list of tokens
        
        if inboundTemplate == None:
            templateName = 'inboundTemplateOnPort' + str(port)
            inboundTemplate = packets.emptyTemplate(templateName)
        
        #STORE PARAMETERS IN actionObject CLASSES
        outboundActionObjectClass._port_ = port #store port number
        inboundActionObjectClass._port_ = port
        
        outboundActionObjectClass._inboundPacketFlag_ = inboundPacketFlag #store inbound packet flag
        inboundActionObjectClass._inboundPacketFlag_ = inboundPacketFlag
        
        outboundActionObjectClass._outboundTemplate_ = outboundTemplate #store outbound packet template
        inboundActionObjectClass._outboundTemplate_ = outboundTemplate
        
        outboundActionObjectClass._inboundTemplate_ = inboundTemplate #store inbound packet template
        inboundActionObjectClass._inboundTemplate_ = inboundTemplate
        
        outboundActionObjectClass.virtualNode = self
        inboundActionObjectClass.virtualNode = self
        
        #UPDATE VIRUAL NODE PORT DICTIONARIES
        self._outboundPortTable_.update({outboundActionObjectClass:port})
        self._inboundPortTable_.update({port:inboundActionObjectClass})
    
    def addDerivedType(self, baseClass, name = None):
        """Creates a new type using baseClass as the base, and adds the baseClass entry in self.__dict__.
        
        baseClass -- the parent class from which to make a derived type.
        name -- if provided, this is the name that should be assigned to the class. If not provided,
                the baseClass __name__ will be used instead.
        
        This is an ugly thing to do, but is necessary because of the way Gestalt should work. The user
        can define actionObject classes in the virtual node. When a call gets made to the class, an
        instance of the actionObject is created. So during initialization, parameters such as which port
        the actionObject class is bound to must be set as class parameters, not instance parameters. All
        well and good except that when subclassing virtual nodes, all of the actionObject classes are not
        copied but just referenced. So there would be a conflict between all virtual nodes that share common
        actionObjects. This function solves the issue by creating a new derived actionObject class and inserting 
        it into the dict of the virtualNode instance.
        
        Note that because the entry happens at the instance level, the original actionObject class can still be accessed
        in the base virtualNode class.
        """
        if name != None:    #use provided name
            typeName = name
        else:   #reuse name of base class
            typeName = baseClass.__name__
            
        newType = type(typeName,(baseClass,) ,{}) #create new type
        self.__dict__.update({typeName:newType})
        return newType
    
class gestaltNode(baseGestaltNode):
    """The standard Gestalt node class.
    
    This class defines the standard functionality that any gestalt node must exhibit, including:
    - provisions for acquiring the node on a network
    - setting the node address
    - coming out of bootloader mode (if applicable)
    
    The key distinction between gestaltNode and baseGestaltNode is that gestaltNode is written
    exactly the same way that a user of the library would write their own virtual nodes. All of the hidden
    functionality is captured in baseGestaltNode. The intention is that this class gets subclassed by all
    Gestalt virtual nodes.
    """
    def init(self):
        """Initialiation routine for gestalt node."""
        self.bootPageSize = 128     #bootloader page size in bytes
        self.bootloaderSupport = True   #default is that node supports a bootloader. For arduino-based nodes this should be set to false by the child node.
    
        #synthetic node parameters
        self.synApplicationMemorySize = 32768  #application memory size in bytes. Used for synthetic responses
        self.synApplicationMemory = [255 for bytePosition in range(self.synApplicationMemorySize)]  #used for synthetic bootloader program load
        self.synNodeURL = "http://www.pygestalt.org/vn/testNode.py"  #fake URL
        self.synNodeAddress = 0 #synthetic node address. Note that eventually will need synthetic node address persistence.
    
    def initPackets(self):
        """Define packet templates."""
        
        #Node Status
        self.statusResponsePacket = packets.template('statusResponse',
                                                     packets.pString('status', 1),  #status is encoded as 'b' for bootloader, and 'a' for application
                                                     packets.unsignedInt('appValidity', 1)) #application validity byte, gets set to 170 if valid
        
        #Bootloader Command
        self.bootCommandRequestPacket = packets.template('bootCommandRequest',
                                                         packets.unsignedInt('commandCode', 1))
        
        self.bootCommandResponsePacket = packets.template('bootCommandResponse',
                                                          packets.unsignedInt('responseCode', 1),
                                                          packets.unsignedInt('pageNumber', 2))
        #Bootloader Write
        self.bootWriteRequestPacket = packets.template('bootWriteRequest',
                                                       packets.unsignedInt('commandCode', 1),
                                                       packets.unsignedInt('pageNumber', 2),
                                                       packets.pList('writeData', self.bootPageSize))
        
        self.bootWriteResponsePacket = packets.template('bootWriteResponse',
                                                        packets.unsignedInt('responseCode', 1),
                                                        packets.unsignedInt('pageNumber', 2))
        #Bootloader Read
        self.bootReadRequestPacket = packets.template('bootReadRequest',
                                                      packets.unsignedInt('pageNumber',2))
        
        self.bootReadResponsePacket = packets.template('bootReadResponse',
                                                       packets.pList('readData', self.bootPageSize))
        
        #Request URL
        self.urlResponsePacket = packets.template('urlResponse',
                                                  packets.pString('URL'))
        
        #Set Address
        self.setAddressRequestPacket = packets.template('setAddressRequest',
                                                   packets.unsignedInt('setAddress', 2))
        
        self.setAddressResponsePacket = packets.template('setAddressResponse',
                                                    packets.pString('URL'))
        
    def initPorts(self):
        """Bind ports to functions and packet templates."""
        
        #Node Status
        self.bindPort(port = 1, outboundFunction = self.statusRequest, inboundTemplate = self.statusResponsePacket)
        
        #Bootloader Command
        self.bindPort(port = 2, outboundFunction = self.bootCommandRequest, outboundTemplate = self.bootCommandRequestPacket,
                      inboundTemplate = self.bootCommandResponsePacket)
        
        #Bootloader Write
        self.bindPort(port = 3, outboundFunction = self.bootWriteRequest, outboundTemplate = self.bootWriteRequestPacket,
                      inboundTemplate = self.bootWriteResponsePacket)
        
        #Bootloader Read
        self.bindPort(port = 4, outboundFunction = self.bootReadRequest, outboundTemplate = self.bootReadRequestPacket,
                      inboundTemplate = self.bootReadResponsePacket)
        
        #URL Request
        self.bindPort(port = 5, outboundFunction = self.urlRequest, inboundTemplate = self.urlResponsePacket)
        
        #Set Address
        self.bindPort(port = 6, outboundFunction = self.setAddressRequest, outboundTemplate = self.setAddressRequestPacket,
                      inboundTemplate = self.setAddressResponsePacket)
        
        #Identify Node
        self.bindPort(port = 7, outboundFunction = self.identifyRequest)
        
        #Synchronization Packet
        self.bindPort(port = 8, outboundFunction = self.syncRequest)
        
        #Reset Node
        self.bindPort(port = 255, outboundFunction = self.resetRequest)
        
        
    def initLast(self):
        """Gets called once node has been initialized."""
        if self.bootloaderSupport:
            self.synBootVectorMode = 'B'    #'B' for bootloader
        else:
            self.synBootVectorMode = 'A'    #'A' for application
    
    # --- Utility Functions ---
    def loadProgram(self, filename):
        '''Loads a program into a Gestalt Node via the built-in Gestalt bootloader.'''
        #initialize hex parser
        parser = utilities.intelHexParser()    #Intel Hex Format Parser Object
        parser.openHexFile(filename)
        parser.loadHexFile()
        pages = parser.returnPages(self.bootPageSize)
        #reset node if necessary to switch to bootloader mode
        nodeStatus, appValid = self.statusRequest()            
        if nodeStatus == 'A':    #currently in application, need to go to bootloader
            self.resetRequest()    #attempt to reset node
            nodeStatus, appValid = self.statusRequest()
            if nodeStatus != 'B':
                notice(self, "ERROR IN BOOTLOADER: CANNOT RESET NODE")
                return False
        #initialize bootloader
        if self.initBootload(): notice(self, "BOOTLOADER INITIALIZED!")
        #write hex file to node
        for page in pages:
            pageData = [addressBytePair[1] for addressBytePair in page]
            pageNumber = self.bootWriteRequest(0, pageData)    #send page to bootloader
            if pageNumber != page[0][0]:
                notice(self, "Error in Bootloader: PAGE MISMATCH: SENT PAGE " + str(page[0][0]) + " AND NODE REPORTED PAGE " + str(pageNumber))
                notice(self, "ABORTING PROGRAM LOAD")
                return False
            notice(self, "WROTE PAGE "+ str(pageNumber))# + ": " + str(pageData)
        #verify hex file from node
        for page in pages:
            pageData = [addressBytePair[1] for addressBytePair in page]
            currentPageNumber = page[0][0]
            verifyData = self.bootReadRequest(currentPageNumber)
            for index, item in enumerate(verifyData):
                if item != pageData[index]:
                    notice(self, "VERIFY ERROR IN PAGE: "+ str(currentPageNumber)+ " BYTE: "+ str(index))
                    notice(self, "VERIFY FAILED")
                    return False
            notice(self, "PAGE " + str(currentPageNumber) + " VERIFIED!")
        notice(self, "VERIFY PASSED")
        #start application
        if not self.runApplication():
            notice(self, "COULD NOT START APPLICATION")
            return FALSE
        #register new node with gestalt interface
        #self.target.nodeManager.assignNode(self)    #registers node with target        
        #need something here to import a new node into self.shell based on URL from node    
        return True
    
    
    
    def initBootload(self):
        """Initializes bootloader."""
        return self.bootCommandRequest('startBootload')
    
    def runApplication(self):
        """Starts the physical node application firmware."""
        return self.bootCommandRequest('startApplication')

    # --- actionObjects ---
    class statusRequest(core.actionObject):
        """Checks whether node is in bootloader or application mode and whether the node application firmware is valid.""" 
        def init(self):
            """Initialization function for statusRequest.

            Return Values:
            status -- "B" for bootloader, "A" for application
            appValidity -- True if application firmware is valid, False if app firmware isn't valid. This is determined
                            by checking if the magic number returned by the node is equal to 170.
            """
            if self.transmitUntilReply():   #transmit to the physical node, with multiple attempts until a reply is received. Default timeout and # of attempts.
                receivedData = self.getPacket()
                status = receivedData['status']
                appValid = (receivedData['appValidity'] == 170)
                return status, appValid
            else:
                notice(self.virtualNode, "Unable to check status.")
                return False, False     
    
        def synthetic(self):
            """Synthetic node service routine handler for statusRequest."""
            return {'status': self.virtualNode.synBootVectorMode, 'appValidity': 170}  #until implement synthetic nodes, this is just a generic reply
    
    
    class bootCommandRequest(core.actionObject):
        """Issues a bootloader commmand to the node."""
        def init(self, command):
            """Initialization function for bootCommandRequest.
            
            command -- 'startBootloader' will switch the node to its bootloader firmware (if availiable)
                       'startApplication' will switch the node to its application firmware (if valid)
                       
            Returns True if successful, or False if unsuccessful.
            """
            
            commandSet = {'startBootloader': 0, 'startApplication': 1}    #command options and corresponding firmware-defined values to send to node.
            responseSet = {'bootloaderStarted':5, 'applicationStarted':9 }    #response options and corresponding firmware-defined values received from node.
            if command in commandSet:   #provided command is valid
                self.setPacket(commandCode = commandSet[command])
                if self.transmitUntilReply(): #transmit to the physical node, with multiple attempts until a reply is received. Default timeout and # of attempts.
                    responseCode = self.getPacket()['responseCode'] #pull response code from packet
                    if command == 'startBootloader' and responseCode == responseSet['bootloaderStarted']: #received valid reply to startBootloader command
                        return True
                    elif command == 'startApplication' and responseCode == responseSet['applicationStarted']: #received valid reply to startApplication command
                        return True
                    else:
                        notice(self.virtualNode, "Received invalid response from node to bootloader command "+ command + ".")
                        return False
                else:
                    notice(self.virualNode, "No response to bootloader command "+ command + ".")
                    return False
            else:
                notice(self.virtualNode, "Bootloader command " + command + " not recognized.")
                return False
        
        def synthetic(self, commandCode):
            """Synthetic node service routine handler for bootCommandRequest."""
            if commandCode == 0:
                self.synBootVectorMode = 'B'
                return {'responseCode': 5, 'pageNumber': 0}  #bootloader started, dummy page number provided
            elif commandCode == 1:
                self.synBootVectorMode = 'A'
                return {'responseCode': 9, 'pageNumber': 0}  #application started, dummy page number provided
            else:
                return False
    
    
    class bootWriteRequest(core.actionObject):
        """Instructs the bootloader to write a provided page of data to the node microcontroller's application code space."""
        def init(self, pageNumber, data):
            """Initialization function for bootWriteRequest
            
            pageNumber -- the memory address of the page to write
            data -- a list of bytes to write to application code space
            
            Returns True if successful, False if unsuccessful.
            """
            self.setPacket(commandCode = 2, pageNumber = pageNumber, writeData = data)
            if self.transmitUntilReply():  #transmit to the physical node, with multiple attempts until a reply is received. Default timeout and # of attempts.
                returnPacket = self.getPacket()
                if returnPacket['responseCode'] == 1:   #valid response code is hardcoded in the firmware
                    return returnPacket['pageNumber']   #response is valid, return page number as provided by the physical node
                else:   #response code didn't match
                    notice(self.virtualNode, "Page write was not successful on physical node end.")
                    return False
            else:
                notice(self.virtualNode, "No response received to page write request.")
                return False
        
        def synthetic(self, commandCode, pageNumber, writeData):
            """Synthetic node service routine handler for bootWriteRequest."""
            if commandCode == 2:    #write page command
                for offset, dataByte in enumerate(writeData):
                    self.virtualNode.synApplicationMemory[pageNumber+offset] = dataByte
                return {'responseCode': 1, 'pageNumber': pageNumber}
            else:
                return False


    class bootReadRequest(core.actionObject):
        """Reads a page from the node's microcontroller application code memory."""
        def init(self, pageNumber):
            """Initialization function for bootReadRequest.
            
            pageNumber -- the memory address location from which to read the page.
            
            Returns a list containing the page data if successful, or False if not.
            """
            self.setPacket(pageNumber = pageNumber)
            if self.transmitUntilReply(): #transmit to the physical node, with multiple attempts until a reply is received. Default timeout and # of attempts.
                return self.getPacket()['readData'] #return memory page
            else:
                notice(self.virtualMachine, "No response received to page write request.")
                return False
        
        def synthetic(self, pageNumber):
            """Synthetic node service routine handler for bootReadRequest."""
            readData = self.virtualNode.synApplicationMemory[pageNumber:pageNumber+self.virtualNode.bootPageSize]
            return {'readData':readData}
        
    
    class urlRequest(core.actionObject):
        """Requests URL to virtual node file"""
        def init(self):
            """Initialization function for urlRequest.
            
            Returns the URL string provided by the node.
            """
            if self.transmitUntilReply(): #transmit to the physical node, with multiple attempts until a reply is received. Default timeout and # of attempts.
                return self.getPacket()['URL']
            else:
                notice(self.virtualNode, 'No URL received.')
                return False
        
        def synthetic(self):
            """Synthetic node service routine handler for urlRequest."""
            return {'URL': self.virtualNode.synNodeURL}     
    
    
    class setAddressRequest(core.actionObject):
        """Associates physical to virtual node by requesting that physically identified node assumes the provided address.
        
        One of the challenges of a networked system is identifying who's who. Gestalt solves this with the following algorithm:
        1) A multicast identification request is sent to all nodes. The request contains a randomly generated address.
        2) Upon receipt of the request, all nodes start blinking an LED.
        3) The user presses the LED on the target node.
        4) The target node assumes the provided address and replies with the URL to its virtual node file.
        
        In the case of "solo Gestalt" nodes, i.e. nodes that are not networked like a USB-connected Arduino, the firmware on the node
        will automatically self-trigger the behavior of (4) upon receipt of the request.
        """
        def init(self, address):
            """Initialization function for setAddressRequest.
            
            address -- the address to be assigned to the target node
            
            Returns URL from target node.
            """
            self.setPacket(setAddress = address)
            if self.transmitUntilReply(mode = 'multicast', timeout = 15):   #transmit to all nodes with multiple attempts seperated by a 15 sec. timeout until reply is received
                return self.getPacket()['URL']                              #Note that the prolonged timeout gives the user time to press a button on the target node.
            else:
                notice(self.virtualNode, 'PHYSICAL NODE WAS NOT IDENTIFIED')
                return False
        
        def synthetic(self, setAddress):
            """Synthetic node service routine handler for setAddressRequest."""
            self.virtualNode.synNodeAddress = setAddress
            return {'URL': self.virtualNode.synNodeURL}
                
    
    class identifyRequest(core.actionObject):
        """Requests that the node identify itself by blinking its LED."""
        def init(self):
            """Initialization function for identifyRequest."""
            self.transmit() #transmit request to node. No response is expected.
            time.sleep(4) #roughly the time that the LED is on.
            return True
        
        def synthetic(self):
            """Synthetic node service routine handler for identifyRequest."""
            notice(self.virtualNode, "SYNTHETIC node blinks its LED at you!")            

    class syncRequest(core.actionObject):
        """Initiates synchronized behavior across multiple networked nodes."""
        def onChannelAccess(self):
            """Transmits a packet when granted access to the interface channel."""
            self.transmit(mode = 'multicast')   #transmit multicast, no reply expected.
        
        def synthetic(self):
            """Synthetic node service routine handler for syncRequest."""
            notice(self.virtualNode, "SYNTHETIC syncronization packet transmitted.")
        
    class resetRequest(core.actionObject):
        """Requests that the node resets itself."""
        def init(self):
            """Initialization function for resetRequest."""
            self.transmit() #transmit reqeuest to node. No response is expected.
            time.sleep(0.1) #give tiem for the watchdog timer to reset.
            return True
        
        def synthetic(self):
            """Synthetic node service routine handler for resetRequest."""
            notice(self.virtualNode, "SYNTHETIC node has been reset")
            pass

class nodeShell(object):
    """A virtual node container to support hot-swapping virtual nodes while maintaining external references.
    
    One of the nice features of Gestalt is the ability to dynamically load virtual nodes from a URL that is returned
    by the physical node firmware. This enables the creator of the physical node to publish the matching virtual node
    online, and means that the user doesn't need to keep track of a bunch of virtual node files. In reality these
    should maybe also get stored on github or something like that!
    
    Note that the node shell has changed significantly from Gestalt v0.6. All of the machinery to acquire a URL from
    the physical node has been moved to the gestalt interface for the sake of clarity. This makes the node shell much
    simpler and independent from the under-the-hood functioning of the nodes themselves. Another change is that
    node address persistence is handled at the interface level (although a parameter may be provided by the user
    directly to the virtual node for cases where the interface is auto-generated).
    """
    def __init__(self, *args, **kwargs):
        """Initialization function for nodeShell.
        
        The node shell's behavior on instantiation varies depending on whether certain keyword arguments are provided.
        If a valid source is given (i.e. a URL, filename, or module name), the virtual node will be loaded directly
        and will not do the song-and-dance of trying to reload the virtual node after talking to the physical node.
        If no arguments are provided, the behavior of the shell will vary depending on the subclass. As an overview,
        four different types of subclasses are expected:
        ->Solo/Independent: arbitrary interface/ arbitrary protocol
        ->Solo/Gestalt: arbitrary interface/ gestalt protocol
        ->Networked/Gestalt: networked gestalt interface/ gestalt protocol
        ->Managed/Gestalt: hardware synchronized gestalt network/ gestalt protocol
        
        To allow these subclasses the opportunity to have different behavior, an _shell_init_ function is called last.
        
        PARAMETERS PULLED FROM KEYWORD ARGUMENTS (and not passed along to child classes):
        filename -- a filename from which to load the virtual node
        URL -- a URL from which to load the virtual node
        module -- a module from which to load the virtual node
        
        NOTE: The shell by definition must pass along function calls to the node. Therefore any attributes of the shell will appear to belong to the node.
        For this reason, all shell attributes are underscored.
        """
        
        #Extract parameters from keyword arguments.
        if "filename" in kwargs:
            self._sourceFilename_ = kwargs.pop("filename")      #NOTE: all shell attributes should be underscored according to note above.
        else:
            self._sourceFilename_ = None
        
        if "URL" in kwargs:
            self._sourceURL_ = kwargs.pop("URL")
        else:
            self._sourceURL_ = None
        
        if "module" in kwargs:
            self._sourceModule_ = kwargs.pop("module")
        else:
            self._sourceModule_ = None
        
        if "name" in kwargs:    #assume temporary name until node is loaded, to use by utilities.notice if load failure occurs.
            self._name_ = kwargs["name"]
            
        #Add shell self-reference to kwargs passed along to node
        kwargs.update({"_shell_":self})
        
        #Define shell flags
        self._nodeLoaded_ = False  #this flag keeps track of whether a virtual node (not including default nodes) has been loaded into the shell.
                                        #Used to prevent the virtual node from cyclically reloading itself over and over if for some reason it is of the
                                        #gestaltNode type (and not a user-created subclass).

        self._virtualNode_ = False  #this is where a reference to the virtual node instance will get stored. Default is False until virtual node successfully loaded.

        if self._sourceFilename_: self._loadNodeFromFile_(self._sourceFilename_, args, kwargs) #load from provided filename
        elif self._sourceURL_: self._loadNodeFromURL_(self._sourceURL_, args, kwargs) #load from provided URL
        elif self._sourceModule_: self._loadNodeFromModule_(self._sourceModule_, args, kwargs) #load from provided module
        else: self._virtualNode_ = False #No source provided to load node. Let the subclass handle that.
        
        self._shellInit_(*args, **kwargs)    #call subclass's init method with provided arguments


    def _setNodeInShell_(self, virtualNode):
        """Performs a sequence of steps to load a node into the shell.
        
        virtualNode -- the node to load into the shell
        """
        self._virtualNode_ = virtualNode    #store reference to virtual node
        if '_name_' in self.__dict__:   #removes the shell's temporary name, so that the attribute request maps onto the node.
            self.__dict__.pop('_name_')
    
    def _setNodeLoaded_(self):
        """Sets the _nodeLoaded_ flag while storing prior state.
        
        The _nodeLoaded_ flag prevents nodes from recursively reloading in an infinite loop by indicating a successful prior load. 
        To accomplish this the flag must be set before it is know whether the node has successfully loaded (i.e. before the node's
        __init__ routine returns.) This method allows this to be done safely by storing the prior version, which can be recalled
        with _revertNodeLoaded_.
        """
        self._oldNodeLoaded_ = self._nodeLoaded_    #store in case need to roll back
        self._nodeLoaded_ = True
    
    def _revertNodeLoaded_(self):
        """Reverts the _nodeLoaded_ flag to its state before the last call to _setNodeLoaded_"""
        self._nodeLoaded_ = self._oldNodeLoaded_
        
        
    def _loadNodeFromFile_(self, filename, args = (), kwargs = {}):
        """Loads a node into the shell from a provided file."""
        try:
            self._setNodeLoaded_()    #pre-mark as node loaded, because this gets checked by new node on instantiation.
            virtualNode = imp.load_source('', filename).virtualNode(*args, **kwargs)    #instantiate virtual node from file
            self._setNodeInShell_(virtualNode)   #set the node into the shell
            return True
        except IOError, error:
            notice(self, "Can not load virtual node from file " + str(filename))
            notice(self, "Error: " + str(error))
            self._revertNodeLoaded_()  #unable to load node, revert flag
            return False
            
    def _loadNodeFromURL_(self, URL, args = (), kwargs = {}):
        """Loads a node into the shell from a provided URL.
        
        Loading follows the following algorithm:
        1) The file pointed to by the URL is downloaded and stored in a temporary file.
        2) We attempt to load a virtualNode from the file
        3) If successful, the file is re-written to its original filename
        4) If not successful, attempt to load the file from the local directory
        
        The reason for only writing to the original filename after a successful load is to prevent overwriting a good virtual node
        file with a 404 reply or some such garbage from a server.
        """
        try:
            vnFilename = os.path.basename(URL)
            urllib.urlretrieve(URL, "temporaryURLNode.py")  #retrieve file from URL
            if self._loadNodeFromFile_("temporaryURLNode.py", args, kwargs):    #try to load node from temporary file
                #insert file copy logic here now that file has been validated
                return True
            else: 
                notice(self, "File dowloaded from URL does not appear to contain a valid virtual node.")
                return False  #error message will be generated by _loadNodeFromFile_
        except StandardError, error:
            notice(self, "Could not load " + str(vnFilename) + " from " + URL)
            notice(self, "Error: " + str(error))
            notice(self, "Attempting to load virtual node from the local directory...")
            self._virtualNode_ = False #unable to load node
            return self._loadNodeFromFile_(vnFilename, args, kwargs)
    
    def _loadNodeFromModule_(self, module, args = (), kwargs = {}):
        """Loads a node into the shell from a provided module.
        
        Note that the class itself should be provided, NOT a class instance.
        """
        try:
            self._setNodeLoaded_()    #pre-mark as node loaded, because this gets checked by new node on instantiation.
            if hasattr(module, 'virtualNode'):  #module has a top-level virtualNode class
                self._setNodeInShell_(module.virtualNode(*args, **kwargs)) #instantiate and set into shell
            else: #assume that module is the virtualNode class
                self._setNodeInShell_(module(*args, **kwargs)) #attempt to insantiate and set into shell
                #maybe should check the type before doing this.
        except AttributeError, error:
            notice(self, "Unable to load virtual node from module")
            notice(self, "Error: " + str(error))
            self._revertNodeLoaded_()   #revert _nodeLoaded_ flag to prior state
            return False
    
    def __getattr__(self, attribute):
        """Forwards any unsupported calls from the shell onto the node.
        
        This function is the crux of the shell. All it does is pass along calls to the virtualNode, thus allowing
        the virtualNodes to be swapped while maintaining external references to the node.
        """
        if self._virtualNode_:  #shell contains a valid virtual node
            if hasattr(self._virtualNode_, attribute):  #check to make sure virtual node has the requested attribute
                return getattr(self._virtualNode_, attribute)   #return the attribute of the virtual node
            else:   #virtual node doesn't have the requested attribute
                notice(self, "Node doesn't have the requested attribute")
                raise AttributeError(attribute)
        else:   #no virtual node has been loaded into the shell
            notice(self, "Node is not initialized")
            raise AttributeError(attribute)
            
    
    def _shellInit_(self, *args, **kwargs):
        """Dummy init function for shell.
        
        This function should be overridden by the child nodes."""
        pass

class gestaltNodeShell(nodeShell):
    """The base node shell for gestalt-based nodes."""
    def _shellInit_(self, *args, **kwargs):
        self._virtualNode_ = gestaltNode(*args, **kwargs)
        