# pyGestalt Machines Library

"""A collection of classes for building machine-level objects.

In the model implemented by pyGestalt, nodes encapuslate hardware-level functionality at a very elemental level.
For example, a stepper motor driver is abstracted as a software object with API methods for e.g. taking a certain
number of steps. When you incorporate a stepper motor into a machine, however, the number of steps no longer has
direct meaning to the user. Rather, they care about the position of the machine (most likely in real-world units like
mm or inches.) This machines library provides classes for building object-oriented machine definitions (to borrow a phrasing
coined by Nadya Peek).
"""

from pygestalt import errors, utilities

class virtualMachine(object):
    def __init__(self, *args, **kwargs):
        """Initializes the virtual machine object.
        
        Initialization occurs by calling a series of init methods. The intention is that these will be overridden by the
        child class.
        
        A few keyword arguments are pulled from the incoming kwarg dictionary:
        
        name -- This name will be used to identify the virtual machine, especially used for storing persistence information.
        interface -- If an interface is provided, this will be set as the VM's interface.
        persistence -- If a persistence argument is used to initialize the virtual machine, this will be used to generate an appropriate
                       persistence manager.
        """
        
        if "name" in kwargs:
            self._name_ = kwargs.pop("name")    #pop name from named arguments, and set as node name. This is used by utilities.notice and for persistence.
        else:
            self._name_ = None  #default value
            
        if "interface" in kwargs:
            self.interface = kwargs.pop("interface")      #the gestalt interface which the virtual machine will set as the interface property.
        else:
            self.interface = None
            
        if "persistence" in kwargs:
            self._persistence_ = kwargs.pop("persistence")
        else:
            self._persistence_ = None            
        
        self.init(*args, **kwargs)
        
        if not self.interface: #no interface was provided
            self.interface = self.defaultInterface()
        
        if self._persistence_:
            candidatePersistenceManager = utilities.generatePersistenceManager(self._persistence_, namespace = self._name_)
            try:
                self.interface.setPersistenceManager(candidatePersistenceManager)
            except:
                notice(self, "Unable to set the persistence manager!")
        
        self.initNodes()
        self.initMechanics()
        self.initLast()

    def init(self, *args, **kwargs):
        pass
    
    def defaultInterface(self):
        return None
    
    def initNodes(self):
        pass
    
    def initMechanics(self):
        pass
    
    def initLast(self):
        pass