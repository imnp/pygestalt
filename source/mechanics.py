#   pyGestalt Mechanics Module

"""A set of objects and methods for defining, analyzing, and utilizing mechanisms."""

#---- INCLUDES ----
import math
from pygestalt import errors, units

class transformer(object):
    """Base class for all types that transform from one state to another.
    
    Mechanisms transform from one domain of machine state to another. For example, converting between rotations of a leadscrew
    to translation of a lead nut. When going in the forward direction (i.e from the actuator to the end effector thru a transmission),
    there is only one solution to end effector state for a given actuator state, assuming that the mechanism is holonomic. An example
    of a non-holonomic mechanism would be a wheeled vehicle. Therefor, the forward direction is always defined as from the actuator to the
    end effector.
    
    There are two types of envisioned transformers:
    elements -- these are one-dimensional transformers that transform from a single state dimension to another. Examples include gears,
                pulleys, leadscrews, etc. While most are linear transformers, they can also be non-linear as in cams.
    
    kinematics --   these are multi-dimensional transformers, usually situated at the end of the mechanical chain, that transform from one
                    multi-dimensional coordinate space to another.  Examples include linear stages such as normal and CoreXY cartesian
                    robots, but also polar bots, robotic arms, five bar linkages,etc.
    """
    
    def __init__(self, forwardTransform, reverseTransform = None, inertia = 0.0):
        """Initializer for the transformer.
        
        forwardTransform -- a dimensional float (units.dFloat), transformation matrix (geometry.array), or a callable object,
                            that transforms from one domain into another in the forward (i.e. actuator -> end effector) direction.
        
        reverseTransform -- if provided, is used to perform the transformation in the reverse direction. Note that this mandatory
                            if anything other than a dFloat is provided as the forward transform.
        
        inertia -- the inertia of the transformer element used for dynamic simulation
        """
        self.forwardTransform = forwardTransform
        self.reverseTransform = reverseTransform
        self.inertia = inertia
    
    def forward(self):
        pass
    
    def reverse(self):
        pass


class singleAxisElement(transformer):
    """A one-dimensional machine element that transforms state from one domain to another."""
    
    def __init__(self, transform, inputUnits, outputUnits, inertia = None):
        """Initializes a new single-axis element.
        
        transform --   either a scalar or a custom transformation type that converts in the forward and reverse directions.
                            If a scalar, will default to the provided units unless units are attached as a dFloat.                         
        inputUnits -- units of the input to the transformer in the forward direction.
        outputUnits -- units of the output from the transformer in the forward direction.
        inertia -- the inertia of the transformer. Can be used for dynamic performance simulations etc. 
        """
        
        
        if type(inputUnits) == units.unit and type(outputUnits) == units.unit: #check for valid units
            self.inputUnits = inputUnits
            self.outputUnits = outputUnits
        else:
            raise errors.UnitError("Input and output units must be of type units.unit")

        if type(transform) == units.dFloat: #provided transform comes with its own units
            if not units.hasUnits(transform, inputUnits, checkEquivalents = True): #dFloat without input units provided
                transform = transform / inputUnits #assume input units in denominator
            if not units.hasUnits(transform, outputUnits, checkEquivalents = True): #dFloat without output units provided
                transform = transform * outputUnits #assume output units in numerator
            transform = transform.convert(self.outputUnits/self.inputUnits) #convert units into units provided on initialization
        else: #transform is a scalar. Give it units.
            transform = self.outputUnits(transform)/self.inputUnits
        #for now we assume any input that isn't a dFloat is a scalar of some type. Later, this needs to be appended to include custom transforms.
        super(singleAxisElement, self).__init__(forwardTransform = transform, reverseTransform = None, inertia = inertia)



#---- ELEMENT TYPES ----

class leadscrew(singleAxisElement):
    """A mechanical element that transforms rotation into translation by means of a helical screw."""
    
    def __init__(self, lead):
        """Initializes a new leadscrew.
        
        lead -- the distance traveled in one revolution of the screw.
                defaults to mm/rev unless other units are provided.
        """
        
        super(leadscrew, self).__init__(transform = lead, inputUnits = units.rev, outputUnits = units.mm)


# class matrix(object):
#     """A base class for creating transformation matrices."""
#     def __init__(self, array):
#         self.array = array
# 
#     def forward(self, input):
#         if self.array[1][1]
#     
# class transformer(object):
#     def __init__(self):
#         self.transformMatrix = matrix([[1,2],[3,4]])
