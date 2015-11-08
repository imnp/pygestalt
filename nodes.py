#   pyGestalt Nodes Module

"""A standard set of base node classes."""


#---- INCLUDES ----
import threading
from pygestalt import core, packets
from pygestalt.utilities import notice


class baseVirtualNode(object):
    """Base class for all virtual nodes"""
    
    def __init__(self, *args, **kwargs):
        """Initializer for all virtual nodes.
        
        Because of the indirect way in which nodes are loaded, the arguments passed to the node
        on instantiation are stored by this routine, and then passed to additional initialization
        functions (_init_ for gestalt nodes) later after the node has been set into the node shell.
        """
        self._initArgs_ = args
        self._initKwargs_ = kwargs

    def _recursiveInit_(self, recursionDepth, *args, **kwargs):
        """Dummy initializer function."""
        print "baseVirtualNode init"
        pass
    
    def _recursiveOnLoad_(self, recursionDepth):
        """Dummy onLoad function.
        
        This is where the recursion terminates"""
        print "baseVirtualNode onLoad"
        pass

class baseGestaltNode(baseVirtualNode):
    """Base class for Gestalt nodes."""
    
    def _recursiveInit_(self, recursionDepth, *args, **kwargs):
        """Recursively initializes Gestalt node.
        
        THIS FUNCTION IS ONLY CALLED INTERNALLY BY _init_
        Initialization occurs in the following steps:
        1) parent class initialization: a call to parentClass._recursiveInit_
        2) init: user initialization routine for defining optional constants etc. that are specific to the node
        3) packets: packet templates are defined here
        4) ports: actionObjects and packets are bound to ports
        5) onLoad: anything that needs to get initialized with the ability to communicate to the node.
        """
        baseClass = self.__class__.mro()[recursionDepth] #base class is determined by the method resolution order indexed by the recursion depth.
        parentClass = self.__class__.mro()[recursionDepth + 1] #parent class is determined the same way
        parentClass._recursiveInit_(self, recursionDepth + 1, *args, **kwargs) #recursively initialize using parent class
        if 'init' in baseClass.__dict__: baseClass.init(self, *args, **kwargs) #run user initialization routine with provided arguments
        if 'initPackets' in baseClass.__dict__: baseClass.initPackets(self) #initialize packets
        if 'initPorts' in baseClass.__dict__: baseClass.initPorts(self) #initialize ports
    
    def _recursiveOnLoad_(self, recursionDepth):
        """Recursively calls onLoad routine across parent virtual node classes.
        
        THIS FUNCTION IS ONLY CALLED INTERNALLY BY _init_, after calling _recursiveInit_
        """
        baseClass = self.__class__.mro()[recursionDepth] #base class is determined by the method resolution order indexed by the recursion depth.
        parentClass = self.__class__.mro()[recursionDepth + 1] #parent class is determined the same way
        parentClass._recursiveOnLoad_(self, recursionDepth + 1) #recursively calls onLoad using parent class        
        if 'onLoad' in baseClass.__dict__: baseClass.onLoad(self) #run after initialization is complete
        
    def _init_(self):
        """Initializes Gestalt Node.
        
        Initialization occurs by calling a sequence of specialized initialization functions. In order to
        support inheritance, and to make sure that all of the inherited functions are called, the parent
        class initialization functions must be called recursively. This function is the entry point into
        the process and starts at a recursion depth of 0.
        
        Note that _initArgs_ and _initKwargs_ are the arguments provided to the virtual node when it was
        first instantiated. They are stored by the baseVirtualNode.
        """
        self._outboundPortTable_ = {}   #stores function:port pairs as assigned by bindPort
        self._inboundPortTable_ = {} #stores port:function pairs as assigned by bindPort
        
        #-- Parse Optional Initialization Parameters --
        if "name" in self._initKwargs_:
            self._name_ = self._initKwargs_.pop("name")    #pop name from named arguments, and set as node name. This is used by utilities.notice
        else:
            self._name_ = None  #default value
            
        if "interface" in self._initKwargs_:
            interface = self._initKwargs_.pop("interface")
            #here need to handle different types of provided interfaces, for when node is generated from within a shell.
            
            
        #-- Initialize Virtual Node Children--
        self._recursiveInit_(0, *self._initArgs_, **self._initKwargs_) #begin recursive initialization at a depth of 0.
        self._recursiveOnLoad_(0)   #begin recursive onLoad
    
    def init(self, *args, **kwargs):
        """User initialization routine for defining optional constants etc. that are specific to the node hardware.
        
        Examples of this might be the crystal frequency, or an ADC reference voltage.
        """
        print "baseGestaltNode init"
        pass
    
    def initPackets(self):
        """Initializes packet templates."""
        pass
    
    def initPorts(self):
        """Bind actionObjects and packets to ports."""
        pass
    
    def onLoad(self):
        """Run any initialization functions that must communicate with the physical node.
        
        An example might be setting some default parameters on the node.
        """
        print "baseGestaltNode onLoad"
        pass
    
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
        self.synBootVectorMode = 'B'    #'B' for bootloader, 'A' for application
        print "gestaltNode init"
    
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
                                                   packets.pList('setAddress', 2))
        
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
        
        #Reset Node
        self.bindPort(port = 255, outboundFunction = self.resetRequest)
        
    def onLoad(self):
        print "gestaltNode onLoad"
        pass
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
                    elif command == 'startAplication' and responseCode == responseSet['applicationStarted']: #received valid reply to startApplication command
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
                return {'responseCode': 5, 'pageNumber': 0}  #bootloader started, dummy page number provided
            elif commandCode == 1:
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
            """Synthetic nod service routine handler for bootReadRequest."""
        
    
    class urlRequest(core.actionObject):
        def init(self):
            pass
    
    class setAddressRequest(core.actionObject):
        def init(self):
            pass
    
    class identifyRequest(core.actionObject):
        def init(self):
            pass
    
    class resetRequest(core.actionObject):
        def init(self):
            pass