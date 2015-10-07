#   pyGestalt Core Module

"""Provides the central elements of the pyGestalt framework."""

#--IMPORTS--

class actionObject(object):
    """A token that embodies the logic behind packet generation.
    
    actionObjects serve a dual role. They contain a set of functions written by the node designer
    that create and interpret packet communication between the virtual and real nodes. They also
    serve as a carrier for the packet as it makes its winding way thru the gestalt framework on
    its way to the interface with the real node. Each call to the action object subclass will generate
    an actionObject dedicated to converting the call into a packet, with the option of also handling a returned
    packet. The reason for bundling a packet with the logic used to create it is that this permits the packet to
    change after it has been generated but before being transmitted. One particular case where this behavior is
    useful is in synchronizing multiple nodes even though the function calls to the nodes are made sequentially.
    In this case synchronization calculations can occur once all of the participant actionObjects are generated.
    
    One of the key differences between this and the previous version of Gestalt (v0.6) is that previously
    actionObjects needed to be wrapped in a serviceRoutine. This is being sidestepped by using class
    properties along with instance properties.
    """
    
    
    def __new__(cls, *args, **kwargs):
        """Intantiation routine for actionObject base class.
        
        When a call is made to the action object class, an instance is created and this function is called.
        Any arguments are passed along to the subclass's init() function, which may either return the instance
        itself or NEED TO REWRITE THIS DESCRIPTION
        """
        newActionObject = object.__new__(cls)   #creates the new actionObject
        newActionObject._init_()    #runs the actionObject base class's initialization. Note that
                                    #__init__ is intentionally not used, because otherwise it would get called twice.
        returnValue = newActionObject.init(*args, **kwargs) # calls the user-defined initialization routine, this time 
                                                            # with any provided arguments.
        
        if returnValue == None:     #if the user initialization doesn't return anything, then return the actionObject
            return newActionObject
        else:                       #otherwise pass along whatever the user has provided
            return returnValue
        
    def _init_(self):
        print "init got called"
        
    def init(self, *args, **kwargs):    #user initialization routine. This should get overridden by the subclass.
        pass