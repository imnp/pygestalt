#   pyGestalt Mechanics Module

"""A set of objects and methods for defining, analyzing, and utilizing mechanisms."""

#---- INCLUDES ----
import math
from pygestalt import errors, units, utilities

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
                            if anything other than an invertable object such as a dFloat is provided as the forward transform.
        
        inertia -- the inertia of the transformer element used for dynamic simulation
        """
        self.forwardTransform = forwardTransform
        if reverseTransform: #a reverse transform was provided, so use that.
            self.reverseTransform = reverseTransform
        else: #no reverse transform provided. Try to invert the forward transform.
            try:
                self.reverseTransform = forwardTransform**-1
            except:
                raise errors.MechanismError("No reverse transform provided. Forward transform [" + str(forwardTransform) + "] is not invertable!")
        self.inertia = inertia
    
    def forward(self, inputState):
        """Transforms state in the forward direction.
        
        inputState -- the input-side state of the transformer.
        
        Note that this function simply multiplies the forward transform by the input state. Any complexity must be handled
        by the __mul__ function of the transform.
        """
        outputState = self.forwardTransform * inputState
        return outputState
    
    def reverse(self, outputState):
        """Transforms state in the reverse direction.
        
        outputState -- the input-side state of the transformer.
        
        Returns the corresponding input-side state.

        Note that this function simply multiplies the reverse transform by the output state. Any complexity must be handled
        by the __mul__ function of the transform.
        """
        inputState = self.reverseTransform * outputState
        return inputState


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


    def forward(self, forwardState):
        """Tranforms from an input state of the tranformer to the corresponding output state.
        
        forwardState -- the forward-going input state of the transformer. MUST be provided as a units.dFloat type.
        
        Note that this function over-rides its base class transformer.forward() function.
        """
        
        if type(forwardState) == units.dFloat:
            convertedForwardState = units.convertToUnits(forwardState, self.inputUnits, strict = True) #convert to input units, don't allow reciprocals
            return self.forwardTransform*convertedForwardState
        else:
            utilities.notice(self, "Input to singleAxisElement transformer must be of type units.dFloat!")
            raise errors.MechanismError("Incorrect input type to singleAxisElement.forward()")
    
    def reverse(self, reverseState):
        """Tranforms in the reverse direction from an output state of the tranformer to the corresponding input state.
        
        inputState -- the input state of the transformer. MUST be provided as a units.dFloat type.
        
        Note that this function over-rides its base class transformer.forward() function.
        """
        
        if type(reverseState) == units.dFloat:
            convertedReverseState = units.convertToUnits(reverseState, self.outputUnits, strict = True) #convert to input units, don't allow reciprocals
            return self.reverseTransform*convertedReverseState
        else:
            utilities.notice(self, "Input to singleAxisElement transformer must be of type units.dFloat!")
            raise errors.MechanismError("Incorrect input type to singleAxisElement.reverse()")

    def transform(self, inputState):
        """Transforms from one state to another based on the provided input units.
          
        This is something of a bonus function, as the recommended useage is to explicitly call forward() or reverse().
        """
          
        if type(inputState) == units.dFloat:
            
            forwardUnitEquivalency = units.getUnitEquivalency(inputState, self.inputUnits(1)) #1 if equivalent, -1 if reciprocals, 0 if not equivalent
            reverseUnitEquivalency = units.getUnitEquivalency(inputState, self.outputUnits(1))
            
            if forwardUnitEquivalency == 1: #inputState units match transform input units. Transform in the forward direction.
                convertedInputState = units.convertToUnits(inputState, self.inputUnits, strict = True) #convert to input units, don't allow reciprocals
                return self.forwardTransform*convertedInputState
            elif reverseUnitEquivalency == 1: #inputState units match transform output units. Transform in the reverse direction.
                convertedInputState = units.convertToUnits(inputState, self.outputUnits, strict = True) #convert to input units, don't allow reciprocals
                return self.reverseTransform*convertedInputState
            else:
                utilities.notice(self, "Input to singleAxisElement transformer cannot be transformed because of a dimensionality mismatch.")
                raise errors.MechanismError("Encountered dimensionality mismatch while attempting transform.")
        else:
            utilities.notice(self, "Input to singleAxisElement transformer must be of type units.dFloat!")
            raise errors.MechanismError("Incorrect input type to singleAxisElement.transform()")
        

#---- SINGLE AXIS ELEMENT TYPES ----

class leadscrew(singleAxisElement):
    """A mechanical element that transforms rotation into translation by means of a helical screw."""
    
    def __init__(self, lead):
        """Initializes a new leadscrew.
        
        lead -- the distance traveled in one revolution of the screw.
                defaults to mm/rev unless other units are provided.
        """
        
        super(leadscrew, self).__init__(transform = lead, inputUnits = units.rev, outputUnits = units.mm)


class gear(singleAxisElement):
    """A mechanical element that transforms torque and angular velocity by means of meshing teeth."""
    
    def __init__(self, reductionRatio):
        """Initializes a new gear set.
        
        reductionRatio -- the ratio between revolutions of the input gear to revolutions of the output gear.
                    this can be calculated by dividing the output pitch diameter by the input pitch diameter,
                        or the output number of teeth by the input number of teeth.
                    
                inputUnits and outputUnits are both in revolutions
        """
        
        super(gear, self).__init__(transform = 1.0/reductionRatio, inputUnits = units.rev, outputUnits = units.rev)


class rotaryPulley(singleAxisElement):
    """A mechanical element that transforms torque and angular velocity by means of a belt connecting two pulleys."""

    def __init__(self, reductionRatio):
        """Initializes a new rotary pulley set.
        
        reductionRatio --   the ratio between revolutions of the input pulley to revolutions of the output pulley.
                            this can be calculated by dividing the diamter of the output pulley by the diameter of the input pulley.
                inputUnits and outputUnits are both in revolutions
        """
        
        super(rotaryPulley, self).__init__(transform = 1.0/reductionRatio, inputUnits = units.rev, outputUnits = units.rev)  


class timingBelt(singleAxisElement):
    """A mechanical element that transforms rotation into translation by means of a toothed pulley meshed with a timing belt."""

    def __init__(self, pulleyPitchDiameter):
        """Initializes a new timing belt.
        
        pulleyPitchDiameter -- the pitch diameter of the timing pulley, in mm.
        """
        
        pitchCircumference = math.pi*pulleyPitchDiameter #transformation ratio is the circumference when going from rev -> travel distance
        super(timingBelt, self).__init__(transform = pitchCircumference, inputUnits = units.rev, outputUnits = units.mm)

class rack(singleAxisElement):
    """A mechanical element that transforms rotation into translation by means of a gear pinion meshed with a flat gear rack."""
    
    def __init__(self, pinionPitchDiameter):
        """Initializes a new rack and pinion.
        
        pinionPitchDiameter -- the pitch diameter of the pinion, in mm.
        """
        
        pitchCircumference = math.pi*pinionPitchDiameter #transformation is circumference when going from rev -> travel distance
        super(rack, self).__init__(transform = pitchCircumference, inputUnits = units.rev, outputUnits = units.mm)

class stepper(singleAxisElement):
    """An electromechanical element that transforms electrical 'step' pulses into rotation."""
    
    def __init__(self, stepSize):
        """Initializes a new stepper motor.
        
        stepSize -- the rotational angle moved by the motor each step, in degrees.
        """
        
        super(stepper, self).__init__(transform = stepSize, inputUnits = units.step, outputUnits = units.deg)
        

#--- ELEMENT CHAINS ---
class chain(transformer):
    """A serial chain of transformer elements."""
    
    def __init__(self, *transformers):
        """Initializes a new transformer chain.
        
        *transformers -- a series of transformer elements, provided as positional arguments in the forward direction.
        """
        self.transformChain = transformers

    def forward(self, forwardState):
        """Tranforms from an input state of the tranformer chain to the corresponding output state.
        
        forwardState -- the forward-going input state of the transformer chain.
        
        Transformation is accomplished by successively feeding the output of each element into the input of the subsequent element.
        
        Note that this function over-rides its base class transformer.forward() function.
        """
        for transformerElement in self.transformChain:
            forwardState = transformerElement.forward(forwardState)
        return forwardState
    
    def reverse(self, outputState):
        """Tranforms from an output state of the tranformer chain to the corresponding input state.
        
        outputState -- the reverse-going output state of the transformer chain.
        
        Transformation is accomplished by successively feeding the input of each element into the output of the subsequent element.
        
        Note that this function over-rides its base class transformer.reverse() function.
        """
        for transformerElement in reversed(self.transformChain):
            outputState = transformerElement.reverse(outputState)
        return outputState



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
