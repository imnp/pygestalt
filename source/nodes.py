#   pyGestalt Nodes Module

"""A standard set of base node classes."""


#---- INCLUDES ----
import threading, Queue
import time
import imp, os, urllib  #for importing files
import copy
from pygestalt import core, packets, utilities, interfaces, config
from pygestalt.utilities import notice, debugNotice
import functools
import inspect, types


#---- GESTALT NODES ----

class baseVirtualNode(object):
    """Base class for all virtual nodes"""
    
    def __init__(self, *args, **kwargs):
        """Default initializer for all virtual nodes.
        
        This should be overridden.
        """
        pass

class baseGestaltVirtualNode(baseVirtualNode):
    """Base class for Gestalt nodes."""

    def __new__(cls, *args, **kwargs):
        """Instantiation routine for baseGestaltVirtualNode base class.
        
        When a call is made to the baseGestaltVirtualNode class, this "magic" function creates the instance.
        It is necessary to define a custom __new__ to support nodes updating themselves on instantiation.
        The object returned by this function may not be the original node instance, but one created recursively.
        """
        newBaseGestaltNode = baseVirtualNode.__new__(cls)
        return newBaseGestaltNode._init_(*args, **kwargs)

    def _init_(self, *args, **kwargs):
        """Initializes Gestalt Node.
        
        Initialization occurs by calling a sequence of specialized initialization functions. In order to
        support inheritance, and to make sure that all of the inherited functions are called, the parent
        class initialization functions must be called. This function is the entry point into
        the process.

        Initialization occurs in the following steps, each across the virtual node instance's method resolution order:
        2) init: user initialization routine for defining optional constants etc. that are specific to the node
        3) packets: packet templates are defined here
        4) ports: actionObjects and packets are bound to ports
        5) last: any actions that must be performed after all subclasses have had a chance to initialize, like setting the node into the interface.
        --- node is bound to interface here ---
        6) onLoad: anything that needs to get initialized with the ability to communicate to the node.
        
        PARAMETERS PULLED FROM KEYWORD ARGUMENTS (and not passed along to child classes):
        name -- the name of the node
        interface -- the interface to use for communication
        _shell_ -- if the node is set within a shell, the shell object passes along a self-reference here
        synthetic -- if True, enables synthetic mode for the node
        
        Returns the active virtual node instance
        """
        
        self._outboundPortTable_ = {}   #stores function:port pairs as assigned by bindPort
        self._inboundPortTable_ = {} #stores port:function pairs as assigned by bindPort
        
        #-- Parse Optional Initialization Parameters --
        self._originalInitArgs_ = copy.copy(args)  #store original arguments for _updateVirtualNode_
        self._originalInitKwargs_ = copy.copy(kwargs)
        
        if "name" in kwargs:
            self._name_ = kwargs.pop("name")    #pop name from named arguments, and set as node name. This is used by utilities.notice and for persistence.
        else:
            self._name_ = None  #default value
            
        if "interface" in kwargs:
            self._interface_ = kwargs.pop("interface")      #the interface on which the node will communicate
        else:
            self._interface_ = None
        
        if "_shell_" in kwargs:
            self._shell_ = kwargs.pop("_shell_")        #if provided, this virtual node has a node shell
        else:
            self._shell_ = None
            
        if "synthetic" in kwargs:
            syntheticArg = kwargs.pop("synthetic")     #synthetic argument has been provided.
        else:
            syntheticArg = False    #no synthetic argument provided, default to false
        
        if syntheticArg == True:    #now that syntheticArg is guaranteed to exist, check if True, and if so, put node in synthetic mode
            self._syntheticMode_ = True
        else:
            self._syntheticMode_ = False
            
        #-- Initialization--
        utilities.callFunctionAcrossMRO(self, "init", args, kwargs)
        utilities.callFunctionAcrossMRO(self, "initPackets")
        utilities.callFunctionAcrossMRO(self, "initPorts")
        utilities.callFunctionAcrossMRO(self, "initLast")
        self._initInterface_()  #initialize interface
        
        if self.runApplication():   #The node has a valid application running. Try to update virtual node if necessary.
            if not self._updateVirtualNode_(self._originalInitArgs_, self._originalInitKwargs_):  #Updates the virtual node object contained within _shell_ based on URL received from node
                utilities.callFunctionAcrossMRO(self, "onLoad")   #begin recursive onLoad if virtual node instance still valid after _updateVirtualNode_
                return self
            else: #returned True: this virtual node instance has been supplanted
                return self._shell_._virtualNode_    #don't use me, use the virtualNode instance already in the shell.
        else:   #could not start application
            utilities.callFunctionAcrossMRO(self, "onLoad")
            return self
             
    
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
        """Initializes the node in the context of an interface by which it will communicate with the outside world.
        
        Initialization occurs in several steps:
        (1) instantiate a gestalt interface if one wasn't provided, and update in originalInitKwargs
        (2) set this virtual node into interface
        (3) set the virtual node's address
        """
        if self._interface_:    #an interface was provided
            if type(self._interface_) != interfaces.gestaltInterface:   #Need to create a gestalt interface. Implies only one node
                #figure out name of new interface
                if self._interface_._name_: #provided interface has a name, pass that along
                    newInterfaceName = self._interface_._name_
                else:   #create a new name
                    if self._name_: #virtual node has a name
                        newInterfaceName = self._name_+"GestaltInterface" #since the interface is dedicated to only one node, it's OK to use this node's name
                    else:
                        newInterfaceName = None #whoever is using the name will figure this out.
                self._interface_ = interfaces.gestaltInterface(name = newInterfaceName, interface = self._interface_) #create a new gestalt interface
            else:
                pass #use the provided interface
        else: #No interface provided
            self._interface_ = interfaces.gestaltInterface() #need to fix this up later... just a temporary fix for now.
        
        self._originalInitKwargs_.update({'interface':self._interface_})    #update input kwargs so that new interface is passed along
        
        newAddress = self._interface_.attachNode(self)    #attach node to interface.
        
        if newAddress: #A new address was provided, therefor must associate
            if isinstance(self, networkedGestaltVirtualNode):    #only display association message if node is a networked gestalt type node.
                notice(self, "Please identify me on the network!")
            self.setAddressRequest(newAddress) #set node address to newAddress
                
    def _isInSyntheticMode_(self):
        """Checks if the node is running in synthetic mode.
        
        Synthetic mode means that the node will synthesize responses as if coming from a physical node. This mode is useful
        for debugging the control system when actual hardware is not avaliable. The node can be placed in synthetic mode in several ways:
        1) synthetic = True is passed as an argument to the node on instantiation
        2) pygestalt.config.synthetic = True
        
        Returns True if the node is running in synthetic mode, otherwise returns False.
        """
        return (config.syntheticMode() or self._syntheticMode_) #list all checks here

    def _updateVirtualNode_(self, args = (), kwargs = {}):
        """Attempts to replace virtual node instance residing inside _shell_ (e.g. self) with an updated version as referenced by the physical node's URL.
        
        This is perhaps one of the weirder initialiation steps of the Gestalt node. As has been discussed previously, when a virtual node is first initialized and
        before it has communicated with its physical node, a default base class (nodes.gestaltVirtualNode) is used. The base class contains just the functionality
        to retreive a URL from the physical node that points to a feature-complete virtual node matching the physical node. _updateVirtualNode_ handles
        retrieving the URL and attempting to instantiate a new virtual node using the referenced file. If successful, this function will replace the base
        virtual node with the retrieved version. All of this is predicated on the node having been instantiated within a shell, and without a source being
        explicitly provided. If no shell is provided it is assumed that the feature-complete virtual node has been directly imported. Keep in mind that the
        present function is part of the base class and will run multiple times.
        
        IMPORTANT NOTE:     By default, only the local directory will be searched for the virtual node, based on the filename specified in the node's
                            returned URL. In order to enable automatic download from the web, config.automaticNodeDownloadOn() must be called, usually
                            from within the virtual machine before the node is declared.
        
        Returns the new virtual node if the node has successfully been replaced, or False if not.
        """ 
        #run some basic checks first
        if self._shell_ == None:    #no shell has been provided
            return False

        if self._shell_._nodeLoaded_:   #a non-default node is already loaded into the shell.
            return False

        nodeURL = self.urlRequest() #get node URL
        
        if config.automaticNodeDownload(): #automatic node downloads are enabled
            return self._shell_._loadNodeFromURL_(nodeURL, args, kwargs) #load from URL
        else: #load from local file
            vnFilename = os.path.basename(URL) #get filename based on URL
            return self._loadNodeFromFile_(vnFilename, args, kwargs) #load from file

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
        
        inboundPacketFlagQueue =  Queue.Queue()   #This queue is used to store an actionObject that should be flagged when a reply has been received.
        
        #GENERATE actionObject CLASSES
        if outboundFunction != None:    #an outbound function has been provided
            outboundActionObjectClass = self._addDerivedType_(outboundFunction)   #this is the class that will actually get called to instantiate action objects
                                                                                #during use. It is a derived class of the provided outboundFunction class. 
            outboundActionObjectClass._baseActionObject_ = outboundFunction            #store the base class for introspection use later
        else: #no outbound function has been provided, must generate one.
            typeName = "outboundActionObjectOnPort"+ str(port)    #make up a name that is unique
            outboundActionObjectClass = self._addDerivedType_(core.genericOutboundActionObjectBlockOnReply, typeName)
            outboundActionObjectClass._baseActionObject_ = core.genericOutboundActionObjectBlockOnReply
        
        if inboundFunction != None: #an inbound function has been provided
            inboundActionObjectClass = self._addDerivedType_(inboundFunction)
            inboundActionObjectClass._baseActionObject_ = inboundFunction
        else: #no inbound function has been provided, must generate one
            typeName = "inboundActionObjectOnPort" + str(port)    #make up a name that is unique
            inboundActionObjectClass = self._addDerivedType_(core.genericInboundActionObject, typeName)
            inboundActionObjectClass._baseActionObject_ = inboundFunction
        
        #GENERATE MISSING PACKET TEMPLATES
        if outboundTemplate == None:
            templateName = 'outboundTemplateOnPort' + str(port)
            outboundTemplate = packets.emptyTemplate(templateName)  #must use an emptyTemplate type because template cannot have an empty list of tokens
        
        if inboundTemplate == None:
            templateName = 'inboundTemplateOnPort' + str(port)
            inboundTemplate = packets.emptyTemplate(templateName)
        
        #STORE PARAMETERS IN actionObject CLASSES
        outboundActionObjectClass._inboundPacketFlagQueue_ = inboundPacketFlagQueue #store a reference to inbound packet flag queue
        inboundActionObjectClass._inboundPacketFlagQueue_ = inboundPacketFlagQueue
        
        outboundActionObjectClass._outboundTemplate_ = outboundTemplate #store outbound packet template
        inboundActionObjectClass._outboundTemplate_ = outboundTemplate
        
        outboundActionObjectClass._inboundTemplate_ = inboundTemplate #store inbound packet template
        inboundActionObjectClass._inboundTemplate_ = inboundTemplate
        
        outboundActionObjectClass.virtualNode = self
        inboundActionObjectClass.virtualNode = self
        
        #UPDATE VIRUAL NODE PORT DICTIONARIES
        self._outboundPortTable_.update({outboundActionObjectClass:port})
        self._inboundPortTable_.update({port:inboundActionObjectClass})
    
    def _addDerivedType_(self, baseClass, name = None):
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
    
    def _getPortNumber_(self, actionObject):
        """Returns the port to which a provided actionObject is bound.
        
        actionObject -- the action object to look up in the node's outbound port table.
        Returns the port number if avaliable, otherwise returns False
        """
        if type(actionObject) in self._outboundPortTable_:
            return self._outboundPortTable_[type(actionObject)]
        else:
            notice(self, "actionObject type " + str(type(actionObject)) + "is not bound to this node.")
            return False
    
    def _getInboundActionObjectFromPortNumber_(self, portNumber):
        """Returns the actionObject type that is bound to an input port number.
        
        portNumber -- the port number of the actionObject to be returned
        """
        if portNumber in self._inboundPortTable_:
            return self._inboundPortTable_[portNumber]
        else:
            notice(self, "No actionObject type is bound to port number " + str(portNumber) + " on this node.")
            return False
        
    def _routeInboundPacket_(self, port, packet):
        """Decodes and routes an inbound packet to an actionObject type in the virtual node.
        
        port -- the port of the target actionObject type
        packet -- a serialized payload packet aimed at the target actionObject type
        """
        actionObjectClass = self._getInboundActionObjectFromPortNumber_(port) #get the actionObject class
        
        actionObjectName = actionObjectClass.__name__
        debugNotice(self, "_gestaltNodeInboundRouter_", actionObjectName + " on port " + str(port) + " (inbound)")        
        
        #make a call to the inbound action object first
        inboundActionObject = actionObjectClass()   #instantiate a new inbound action object
        inboundActionObject._decodeAndSetInboundPacket_(packet) #provides packet to the inbound action object
        inboundActionObject.onReceive() #run the inbound action object's onReceive method now that packet has been provided
        
        outboundActionObject = actionObjectClass._getActionObjectFromInboundPacketFlagQueue_()  #attepts to retrieve an actionObject instance from the class's inboundPacketFlagQueue
        if outboundActionObject:
            outboundActionObject._decodeAndSetInboundPacket_(packet)    #store decoded packet in the outbound actionObject instance
            outboundActionObject._inboundPacketFlag_.set()  #set flag on outbound actionObject instance to indicate that a packet has been received
        
        return True
    
    def setDefaultInterface(self, interface):
        """Sets the default interface that the virtual node should use if none is provided on instantiation.
        
        interface -- the interface that should be used if no other interface has been provided to the node.
        
        If no interface is passed to the node's _init_ on instantiation, the default interface provided to this function will be used instead.
        This is typically called from within the virtual node's init routine, and makes it possible for users to simply import the virtual node
        directly and have it attach to a pre-suggested interface. This is particularly useful with standalone nodes.
        
        Returns True if the default interface was used, or False if an alternate interface was already provided.
        """
        if self._interface_ == None:
            self._interface_ = interface
            return True
        else:
            return False
        
    
class gestaltVirtualNode(baseGestaltVirtualNode):
    """The standard Gestalt node class.
    
    This class defines the standard functionality that any gestalt node must exhibit, including:
    - provisions for acquiring the node on a network
    - setting the node address
    - coming out of bootloader mode (if applicable)
    
    The key distinction between gestaltVirtualNode and baseGestaltVirtualNode is that gestaltVirtualNode is written
    exactly the same way that a user of the library would write their own virtual nodes. All of the hidden
    functionality is captured in baseGestaltVirtualNode. The intention is that this class gets subclassed by all
    Gestalt virtual nodes.
    """
    def init(self, *args, **kwargs):
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
            pageNumber = self.bootWriteRequest(page[0][0], pageData)    #send page to bootloader
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
        if not self.runApplication(enforceValidity = False):    #validity flag doesn't get set until application firmware runs, so need to skip check first time after loading new firmware
            notice(self, "BOOTLOADER COULD NOT START APPLICATION")
            return False
        else:
            notice(self, "NEW FIRMWARE " + str(filename) + " LOADED SUCCESSFULLY")
        #register new node with gestalt interface
        #self.target.nodeManager.assignNode(self)    #registers node with target        
        #need something here to import a new node into self.shell based on URL from node    
        return True
    
    
    
    def initBootload(self):
        """Initializes bootloader."""
        return self.bootCommandRequest('startBootloader')
    
    def runApplication(self, enforceValidity = True):
        """Attempts to starts the physical node application firmware.
        
        enforceValidity -- if True, ensure that the application firmware is valid before running. This option is used by the bootloader.
        
        Returns True if successful, or False if unsuccessful.
        """
        
        nodeStatus, appValid = self.statusRequest() #get current status of node
        
        if enforceValidity:
            if not appValid:    #application is not valid
                notice(self, "Application firmware is invalid!")
                return False
        
        if nodeStatus == 'B':   #in bootloader mode, attempt to switch to application mode
            if not self.bootCommandRequest('startApplication'):   #cannot switch to application mode
                notice(self, "Unable to switch node to application mode.")
                notice(self, "Running in bootloader mode!")
                return False
            else:
                return True


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
            if self.transmitUntilResponse():   #transmit to the physical node, with multiple attempts until a reply is received. Default timeout and # of attempts.
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
                if self.transmitUntilResponse(): #transmit to the physical node, with multiple attempts until a reply is received. Default timeout and # of attempts.
                    responseCode = self.getPacket()['responseCode'] #pull response code from packet
                    if command == 'startBootloader' and responseCode == responseSet['bootloaderStarted']: #received valid reply to startBootloader command
                        return True
                    elif command == 'startApplication' and responseCode == responseSet['applicationStarted']: #received valid reply to startApplication command
                        return True
                    else:
                        notice(self.virtualNode, "Received invalid response from node to bootloader command "+ command + ".")
                        return False
                else:
                    notice(self.virtualNode, "No response to bootloader command "+ command + ".")
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
            if self.transmitUntilResponse():  #transmit to the physical node, with multiple attempts until a reply is received. Default timeout and # of attempts.
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
            if self.transmitUntilResponse(): #transmit to the physical node, with multiple attempts until a reply is received. Default timeout and # of attempts.
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
            if self.transmitUntilResponse(): #transmit to the physical node, with multiple attempts until a reply is received. Default timeout and # of attempts.
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
            if self.transmitUntilResponse(mode = 'multicast', timeout = 15):   #transmit to all nodes with multiple attempts seperated by a 15 sec. timeout until reply is received
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
            self.virtualNode.syntheticSync() #call syntheticSync method in virtual node, so that it can act on a synchronization request

    def syntheticSync(self):
        """Called by syncRequest when in synthetic mode.
        
        It is intended that this function is overridden by the virtual node child class.
        """
        pass

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

class soloGestaltVirtualNode(gestaltVirtualNode):
    """A gestalt node subclass that is not on a network bus with other nodes."""
    pass
    
    
class arduinoGestaltVirtualNode(soloGestaltVirtualNode):
    """A gestalt node subclass that automatically sets the appropriate serial interface and baud rate to talk with arduino-based Gestalt nodes.
    
    Custom-made Gestalt nodes typically use a 18.432MHz crystal to eliminate timing errors at all standard baud rates.
    However, the Arduino Uno and equivalents ships with a 16MHz crystal, so the firmware uses a 38400 baud rate.
    This rate has the lowest error of all speeds that are well-supported on all operating systems. (Initially tried 76800,
    which worked well on a Mac but not on Linux.)
    
    While the standard gestalt node class does not automatically create a serial interface, knowing that this virtual
    node is an arduino means we can assume it is communicating over a USB to Serial adapter if not otherwise specified.
    """
    
    def init(self, *args, **kwargs):
        #need to provide a default interface, or update the baud rate in a serial interface was specified manually
        if self._interface_ == None: #no interface was provided, create a new serial interface
            if 'port' in kwargs:    #a port path was provided, use that
                portPath = kwargs['port']
            else:
                portPath = None
            self.setDefaultInterface(interfaces.serialInterface(port = portPath, baudrate = 38400))
            
        elif type(self._interface_) == interfaces.serialInterface:  #a serial interface was provided
            self._interface_.updateBaudrateIfDefault(38400) #attempt to change the default baudrate
            if self._interface_.baudrate != 38400:  #check the baudrate. If it doesn't match, then an incorrect user-provided baudrate supersceded the above call.
                notice(self, "NOTICE: The user-provided baudrate of " + str(self._interface_.baudrate) + " is not standard for the Arduino Gestalt Library.")
        
        elif type(self._interface_) == interfaces.gestaltInterface: #a gestalt interface was provided
            interface = self._interface_._interface_
            if type(interface) == interfaces.serialInterface:
                interface.updateBaudrateIfDefault(38400)
                if interface.baudrate != 38400:  #check the baudrate. If it doesn't match, then an incorrect user-provided baudrate supersceded the above call.
                    notice(self, "NOTICE: The user-provided baudrate of " + str(interface.baudrate) + " is not standard for the Arduino Gestalt Library.")
            else: #some other interface was provided
                notice(self, "NOTICE: Unable to confirm that the provided interface's baud rate is appropriate for the Arduino Gestalt Library")
                
        else: #some other interface was provided
            notice(self, "NOTICE: Unable to confirm that the provided interface's baud rate is appropriate for the Arduino Gestalt Library")

class networkedGestaltVirtualNode(gestaltVirtualNode):
    """A gestalt node subclass that is on a network bus with other nodes.
    
    This has implications for how the node associates with its virtual node counterpart, and in particular means that a message with the node
    name should be displayed on association, to notify the user that they need to press a button.
    """
    
    def init(self, *args, **kwargs):
        #If no interface was provided, assign a default serial interface
        if self._interface_ == None: #no interface was provided, create a new serial interface
            if 'port' in kwargs:    #a port path was provided, use that
                portPath = kwargs['port']
            else:
                portPath = None
            self.setDefaultInterface(interfaces.serialInterface(port = portPath)) #baud rate defaults to 115200 as specified in interfaces.serialInterface

#---- NODE SHELLS ----
 
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
                                        #gestaltVirtualNode type (and not a user-created subclass).

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
        """Loads a node into the shell from a provided file.
        
        filename -- the file to load as a module
        args -- a tuple of positional arguments to pass to the node on instantiation
        kwargs -- a dictionary of keyword arguments to pass to the node on instantiation
        
        returns the loaded virtual node
        """
        
        try:
            self._setNodeLoaded_()    #pre-mark as node loaded, because this gets checked by new node on instantiation.
            virtualNode = imp.load_source('', filename).virtualNode(*args, **kwargs)    #instantiate virtual node from file
            self._setNodeInShell_(virtualNode)   #set the node into the shell
            return virtualNode
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
            virtualNode = self._loadNodeFromFile_("temporaryURLNode.py", args, kwargs)
            if virtualNode:    #try to load node from temporary file
                #insert file copy logic here now that file has been validated
                return virtualNode
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
                virtualNode = module.virtualNode(*args, **kwargs)
                self._setNodeInShell_(virtualNode) #instantiate and set into shell
                return virtualNode
            else: #assume that module is the virtualNode class
                virtualNode = module(*args, **kwargs)
                self._setNodeInShell_(virtualNode) #attempt to insantiate and set into shell
                return virtualNode
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
        if not self._virtualNode_: #no virtual node was provided, so use a default gestalt node
            self._virtualNode_ = gestaltVirtualNode(*args, **kwargs)

class soloGestaltNode(gestaltNodeShell):
    """The node shell type for solo (non-networked) gestalt nodes.
    
    This container is provided to make user code more clear in terms of the type of node. For now, there is no functional difference between
    solo and networked gestalt nodes at the base virtual node level.
    """
    def _shellInit_(self, *args, **kwargs):
        if not self._virtualNode_: #no virtual node was provided, so use a default gestalt node
            self._virtualNode_ = soloGestaltVirtualNode(*args, **kwargs)    

class networkedGestaltNode(gestaltNodeShell):
    """The node shell type for networked gestalt nodes.
    
    This container is provided to make user code more clear in terms of the type of node. For now, there is no functional difference between
    solo and networked gestalt nodes at the base virtual node level.
    """
    def _shellInit_(self, *args, **kwargs):
        """Initializes the virtual node shell.
        
        While there are no functional differences at present between a solo and networked node, a user message is displayed during address 
        acquisition if the node type is a networkedGestaltNode. In order to trigger this message, we over-ride the type of node used on default
        to be a networkedGestaltVirtualNode.
        """
        if not self._virtualNode_: #no virtual node was provided, so use a default gestalt node
            self._virtualNode_ = networkedGestaltVirtualNode(*args, **kwargs)
                
class arduinoGestaltNode(gestaltNodeShell):
    """The node shell type for arduino-based gestalt nodes.
    
    This container is modified slightly from the gestaltNodeShell because it defaults to a arduino gestalt node
    if no virtual node source is provided by the user.
    
    """
    def _shellInit_(self, *args, **kwargs):
        if not self._virtualNode_: #no virtual node was provided, so use a default gestalt node
            self._virtualNode_ = arduinoGestaltVirtualNode(*args, **kwargs)  


#---- COMPOUND NODES ----  
def pattern(numberOfNodes = 1, names = None, interface = None, filename = None, nodeType = None):
    """Returns a compoundNode array of a single node type.
    
    numberOfNodes -- the number of nodes to be created. Default value is 1.
    names -- names to be used for each node. If a tuple or list is provided, one node will be created per name. If a string is provided,
             and numberOfNodes is provided, then the name will be patterned. Otherwise a single node will be created and returned as a compound
             node. If no name is provided, then a generic name will be used for each node.
    interface -- the interface to be provided to each node. For networkedGestaltNodes, a common default interface will be provided.
    filename -- the filename of the virtual node. If not provided, it will need to be provided by the node on the network.
    nodeType -- a pyGestalt node type. The default is networkedGestaltNode, as this is the intended use pattern for compoundNode. However,
                types such as soloGestaltNode and arduinoGestaltNode could be used.
                
    Returns a compoundNode containing the pattern of nodes.
    """
    # Determine number of nodes, and names
    if type(names) == list or type(names) == tuple: # multiple names are provided
        numberOfNodes = len(names) #derive number of nodes from number of names
    else: #need to generate a list of names
        if names == None: names = "PatternedNode" #No name is provided, so use a generic one
        names = [names + "-" + str(index+1) for index in range(numberOfNodes)]
    
    # Set Node Type
    if nodeType == None: nodeType = networkedGestaltNode
    
    # Create a default interface
    if nodeType == networkedGestaltNode and interface == None:
        print "CREATING MULTPLE NODES: NO INTERFACE PROVIDED. DEFAULTING TO GESTALT + SERIAL @ 115.2kbps OVER FTDI"
        serialInterface = interfaces.serialInterface(baudrate = 115200, interfaceType = 'ftdi')
        interface = interfaces.gestaltInterface(name = "auto generated Gestalt interface", interface = serialInterface)
    
    nodes = tuple([nodeType(name = nodeName, filename = filename, interface = interface) for nodeName in names])
        
    return compoundNode(*nodes)       
        
    


class compoundNode(object):
    """Distributes and synchronizes function calls across multiple nodes.
    
    Grouping nodes together under the banner of a 'compound node' serves two purposes. First, it provides convenience by allowing a single
    function call to be issued to multiple nodes. For example, five nodes might have their firmware updated by a single call to a
    containing compound node. Second, nodes can be functionally grouped together to synchronously perform tasks. This is perhaps one of 
    the most exciting elements of Gestalt -- being able to logically treat three single-axis nodes as a single three-axis node.
    
    A call to a compound node is distributed to the consituent nodes according to the following rule, depending on the type of the
    positional or named argument that was provided:
        tuple -- each element in the tuple is uniquely distributed to individual constituent nodes based on the position inside the tuple.
        everything else -- each element is distributed to all constituent nodes.
        
    For example: myCompoundNode.functionName((1,2,3), 4, thisSetting = 5) would distribute as node1.functionName(1,4, thisSetting = 5),
    node2.functionName(2,4, thisSetting=5), and node3.functionName(3,4, thisSetting = 5).
    """
    
    def __init__(self, *nodes):
        """Initializes the compound node.
        
        nodes -- any number of virtualNode objects, provided as positional arguments.
        
        Note that the order in which the virtual nodes are provided will dictate the mapping between function calls to the compound
        node and how they are distributed to the constituent nodes (provided that the arguments of the function calls are within
        tuples for distribution, per above.)
        """
        self._nodes_ = nodes
        self._size_ = len(nodes)
        self._name_ = '[' + ''.join([str(node._name_) + ',' for node in self._nodes_])[:-1] + ']'
        self._interface_ = self._validateInterfaceConsistency_() #stores the common interface object, or False if none exists.
        if not self._interface_: notice(self, 'Warning - Not all members of compound node share a common interface!') #non-blocking warning
    
    def __getattr__(self, attribute):
        """Forwards any calls on the compoundNode onto its constituent nodes according to distribution rules.
        
        When a call is made on the compound node, it will be passed along to all constituent nodes. If arguments are provided,
        they will also be forwarded along. Any arguments that are provided as tuples will trigger "unique distribution", meaning
        that each element of the tuple will be positionally mapped to the constituents in the _nodes_ list.
        
        Returns all returned values, or an actionSet object if unique distribution is triggered by tuples in the input arguments
        and all returned values are either actionObjects or actionSets.
        """
        
        # We use functools.partial, which will return a callable object that wraps core.distributedFunctionCall, but preloads
        # some key pre-determined arguments that set up how the distribution occurs.
        if self._okToSync_(attribute):
            syncToken = core.syncToken
        else:
            syncToken = False
        
        return functools.partial(core.distributedFunctionCall, self, self._nodes_, attribute, syncToken) #distributedFunctionCall(owner, targetList, attribute, syncTokenType, *arguments, **keywordArguments)
    
    def _validateInterfaceConsistency_(self):
        """Tests whether all constituent nodes share a common interface.
        
        Returns the interface object if all constituent nodes share a common interface. Otherwise returns False.
        """
        interfaces = [node._interface_ for node in self._nodes_] #a list of all constituent node interfaces
        if all(interface == interfaces[0] for interface in interfaces): #check that all interfaces are the same
            return interfaces[0] #return the common interface
        else:
            return False #no common interface, return False
    
    def _okToSync_(self, attribute):
        """Determines whether all targets can accept a synchronization token.
        
        All actionObjects silently accept Sync tokens and leave it up to the user what to do with them. However, it is common practice
        for a virtual node to wrap the actionObject call in a function that does some additional logic. For example, a stepper motor
        controller's setMotorCurrent() may be a function guiding the user thru a process like turning a potentiometer, rather than an actionObject. 
        These user-defined functions may not accept "sync" as an input parameter. Therefore, we want to make sure that all targets of the distributed 
        function call are actually able to accept a sync token before we provide one.
        
        Returns True if all targets can accept a sync token, or False if not.
        """
        
        return all([self._acceptsSyncToken_(node, attribute) for node in self._nodes_])
    
    def _acceptsSyncToken_(self, node, attribute):
        """Determines whether a target can accept a synchronization token.
        
        Returns True if:
            - The target is an actionObject class, because these by default accept sync tokens
            - The target is a FUNCTION or METHOD that either explicitly takes 'sync' as an argument, or accepts kwargs.
        Returns False if none of the above conditions are met. Note that if the target is a class other than actionObject, False will be returned by default.
        """
        if hasattr(node, attribute): #first check that node actually has the requested attribute
            target = getattr(node, attribute)
            if type(target) == core.actionObject: #actionObject, so return True by default
                return True
            elif inspect.isfunction(target) or inspect.ismethod(target): #function, need to check if it accepts sync, either explicitly or as **kwargs
                args, varargs, keywords, defaults = inspect.getargspec(target)
                if 'sync' in args or keywords: #either accepts sync explicitly as an argument, or accepts multiple keyword arguments
                    return True
            else:
                return False
        else:
            return False
        
    
    
    
    
