#   pyGestalt Nodes Module

"""A standard set of base node classes."""

class baseVirtualNode(object):
    '''Base class for all virtual nodes'''
    
    def __init__(self, *args, **kwargs):
        '''Initializer for all virtual nodes.
        
        Because of the indirect way in which nodes are loaded, the arguments passed to the node
        on instantiation are stored by this routine, and then passed to additional initialization
        functions later after the node has been provided with all necessary references during load.
        '''
        self._initArgs_ = args
        self._initKwargs_ = kwargs

    def _recursiveInit_(self, _recursionDepth_, *args, **kwargs):
        '''Dummy initializer function.'''
        pass

class baseGestaltNode(baseVirtualNode):
    '''Base class for Gestalt nodes.'''
    
    def _recursiveInit_(self, recursionDepth, *args, **kwargs):
        '''Recursively initializes Gestalt node.
        
        THIS FUNCTION IS ONLY CALLED INTERNALLY BY _init_
        Initialization occurs in the following steps:
        1) parent class initialization: a call to super()_init_()
        2) parameters: optional constants etc. that are specific to the node
        3) packets: packet templates are defined here
        4) ports: actionObjects and packets are bound to ports
        5) onLoad: anything that needs to get initialized with the ability to communicate to the node.
        '''
        baseClass = self.__class__.mro()[recursionDepth] #base class is determined by the method resolution order indexed by the recursion depth.
        parentClass = self.__class__.mro()[recursionDepth + 1] #parent class is determined the same way
        parentClass._recursiveInit_(self, recursionDepth + 1, *args, **kwargs) #recursively initialize using parent class
        if 'initParameters' in baseClass.__dict__: baseClass.initParameters(self, *args, **kwargs) #initialize parameters
        if 'initPackets' in baseClass.__dict__: baseClass.initPackets(self, *args, **kwargs) #initialize packets
        if 'initPorts' in baseClass.__dict__: baseClass.initPorts(self, *args, **kwargs) #initialize ports
        if 'onLoad' in baseClass.__dict__: baseClass.onLoad(self, *args, **kwargs) #run after initialization is complete
        
    def _init_(self, *args, **kwargs):
        '''Initializes Gestalt Node.
        
        Initialization occurs by calling a sequence of specialized initialization functions. In order to
        support inheritance, and to make sure that all of the inherited functions are called, the parent
        class initialization functions must be called recursively. This function is the entry point into
        the process and starts at a recursion depth of 0.
        '''
        self._recursiveInit_(0, *args, **kwargs) #begin recursive initialization at a depth of 0.
    
    def initParameters(self, *args, **kwargs):
        '''Initializes optional constants etc. that are specific to the node hardware.
        
        Examples of this might be the crystal frequency, or an ADC reference voltage.
        '''
        pass
    
    def initPackets(self, *args, **kwargs):
        '''Initializes packet templates.'''
        pass
    
    def initPorts(self, *args, **kwargs):
        '''Bind actionObjects and packets to ports.'''
        pass
    
    def onLoad(self, *args, **kwargs):
        '''Run any initialization functions that must communicate with the physical node.
        
        An example might be setting some default parameters on the node.
        '''
        pass
    
        