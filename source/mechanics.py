#   pyGestalt Mechanics Module

"""A set of objects and methods for defining, analyzing, and utilizing mechanisms."""

#---- INCLUDES ----
import math
from pygestalt import errors, units, utilities, geometry

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
        
        forwardTransform -- a dimensional float (units.dFloat), transformation matrix (geometry.matrix), or a callable object,
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
        
        self.dimensions = self.calculateDimensions()
    
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

    def calculateDimensions(self):
        """Determines and returns the input and output dimensions of the transformer.
        
        The dimensionality of the transformer is defined as the number of degrees of freedom it accepts as inputs and that it
        provides as outputs.
        
        returns dimensions as a tuple in the format (outputDimension, inputDimension), where:
            outputDimension -- the number of degrees of freedom of the transformer output
            inputDimension -- the number of degrees of freedom of the transformer input
            
        Note that the order is (output, input) to maintain compatibility with matrix sizes and indices as (rows, columns), where
        the number of columns corresponds to the inputs of the transformation matrix, and the number of rows the outputs.
        """
        if isinstance(self.forwardTransform, float):
            outputDimension, inputDimension = (1,1) #transform is a (dimensional) floating point number, so input and output dimensions are 1
        else:
            try: #see if forwardTransform implements getSize()
                outputDimension, inputDimension = self.forwardTransform.getSize()
            except AttributeError: #no getSize is implemented
                outputDimension, inputDimension = (None, None) #return (None, None) as a placeholder since no size can be determined.
        
        return (outputDimension, inputDimension)
    
    def getSize(self):
        """Returns the pre-calculated input and output dimensions of the transformer.
        
        returns dimensions as a tuple in the format (outputDimension, inputDimension), where:
            outputDimension -- the number of degrees of freedom of the transformer output
            inputDimension -- the number of degrees of freedom of the transformer input
        
        Note that this method is called getSize rather than getDimensions to keep it consistent with the geometry.array method. It is still
        slightly confusing because the size of an array might be e.g. 3x3 but its dimensionality is 2. But we think of the dimensionality of a
        transformer as 1D, 2D, 3D, etc...
        """
        return self.dimensions
                
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
        
class invert(transformer):
    """A single-axis utility element that inverts the sign of the signal passing thru it."""
    
    def __init__(self):
        """Initializes a new inverter."""
        super(invert, self).__init__(forwardTransform = -1.0)

#---- MULTI-AXIS KINEMATIC TRANSFORMERS ----
class matrixTransformer(transformer):
    """A matrix-based transformer.
    
    While the transformer class by default accepts matrices as forward and reverse transforms, the formatting expected
    on the input and output of matrices must be 2D, whereas for transformers it is expected to be 1D. This class
    performs the necessary pre-formatting of inputs and post-formatting of results.
    """
    
    def forward(self, forwardState):
        """Transform in the forward direction.
        
        forwardState -- a list-formatted single-row array containing the input state of the transformer.
        
        The purpose of this method is just to convert the input state into a 2D column matrix so it can be multiplied
        by the forward transform matrix.
        """
        forwardStateMatrix = geometry.matrix(forwardState).transpose()
        outputStateMatrix = self.forwardTransform*forwardStateMatrix
        outputState = list(outputStateMatrix.transpose())[0]
        return outputState
    
    def reverse(self, reverseState):
        """Transform in the reverse direction.
        
        reverseState -- a list-formatted single-row array containing the output state of the transformer.
        
        The purpose of this method is just to convert the output state into a 2D column matrix so it can be multiplied
        by the reverse transform matrix. 
        """
        reverseStateMatrix = geometry.matrix(reverseState).transpose()
        inputStateMatrix = self.reverseTransform*reverseStateMatrix
        inputState = list(inputStateMatrix.transpose())[0]
        return inputState   
    
class corexy(matrixTransformer):
    """CoreXY or H-bot based kinematics.
    
    See www.corexy.com
    """
    def __init__(self):
        """Initializes a new corexy transformer."""
        forwardTransform = geometry.matrix([[0.5, 0.5], [0.5, -0.5]])
        super(corexy, self).__init__(forwardTransform = forwardTransform)


#---- UTILITY TRANSFORMERS ----
class router(transformer):
    """A transformer that routes from a set of inputs to a set of outputs"""
    def __init__(self, forwardRoutingMap):
        """Initializes the routing transformer.
        
        forwardRoutingMap -- an ordered list whose indices correspond to the input positions, and whose values correspond to output positions.
                      [output[0], output[1], ..., output[n]]
                      
        For example, to route input[0] to output[1] and vice versa, the routing map would be [1,0]. Note that the length of the
        routingMap must exactly equal the number of inputs and outputs, and that all mappings must be specified.
        """
        self.forwardRoutingMap = forwardRoutingMap
        
        ###Need to add some checks here to make sure the routing map is valid
        
        self.reverseRoutingMap = list(range(len(forwardRoutingMap))) #placeholder for reverse routing map
        for index, value in enumerate(self.forwardRoutingMap): #build reverse routing map
            self.reverseRoutingMap[value] = index
            
        self.dimensions = self.calculateDimensions()

    def forward(self, forwardState):
        return [forwardState[index] for index in self.forwardRoutingMap]
    
    def reverse(self, reverseState):
        return [reverseState[index] for index in self.reverseRoutingMap]

    def calculateDimensions(self):
        """Calculates and returns the dimensions of the router."""
        routingMapSize = len(self.forwardRoutingMap)
        return (routingMapSize, routingMapSize)        


class offset(transformer):
    """A transformer that applies a constant offset.
    
    This is useful for implementing homing and zeroing.
    """
    def __init__(self, dof):
        """Initializes the offset.
        
        dof -- the number of degrees of freedom of the offset transformer.
        """
        self.dof = dof
        self.dimensions = self.calculateDimensions()
        self.offset = geometry.array([0.0 for degreeOfFreedom in range(self.dof)])
    
    def calculateDimensions(self):
        """Calculates and returns the dimensions of the offset.
        
        The dimensions of the offset equals the number of degrees of freedom for both the inputs and the outputs.
        """
        return (self.dof, self.dof)

    def set(self, offsetArray):
        """Sets the offset to be internally applied by the transformer.
        
        offsetArray -- a list-formatted 1D array containing the offsets to apply. Note that the sign is in the forward direction, 
                        i.e. for an offset of [3,4], output = input + offset.
                        
        This method is useful for setting the absolute position of a transformer chain, as is done in homing.
        """
        
        if self.validateOffset(offsetArray):
            self.offset = geometry.array(offsetArray)
        else:
            raise errors.MechanismError("Unable to set offset.")
        
    def adjust(self, adjustmentArray):
        """Applies an adjustment to the offset.
        
        adjustmentArray -- a list-formatted array containing the values by which to change the internal offset.
        
        This method is useful for changing the desired output state of a transformer chain by a certain amount, as is done in zeroing.
        """
        if self.validateOffset(adjustmentArray):
            self.offset = self.offset + geometry.array(adjustmentArray)
        else:
            raise errors.MechanismError("Unable to adjust offset.")

    def forward(self, forwardState):
        """Transform in the forward direction.
        
        forwardState -- a single value or list-formatted array containing the input state of the transformer.
        
        Offset is applied by adding it to forwardState
        """
        return list(forwardState + self.offset)
    
    def reverse(self, reverseState):
        """Transform in the reverse direction.
        
        reverseState -- a single value or list-formatted array containing the output state of the transformer.
        
        Offset is applied by subtracting it from reverseState
        """
        return list(reverseState - self.offset)

    def validateOffset(self, offsetArray):
        """Validates that a provided offset array is compatible with the transformer.
        
        offsetArray -- the offset array to be validated.
        
        Returns True if validation passes, or False if not.
        """                       
        offsetSize = geometry.arraySize(offsetArray)
        if len(offsetSize) > 1:
            utilities.notice(self, "Provided offset array has a dimension of "+ str(len(offsetSize)) + ", and must be 1D!")
            return False
        elif offsetSize[0]!= self.dof:
            utilities.notice(self, "Provided offset has a size of " + str(offsetSize[0]) + " DOF, but the transformer has " + str(self.dof)+ " DOF.")
            return False
        else:
            return True        


class passThru(transformer):
    """A transformer that acts as a direct pass-thru of the input to the output.
    
    This type of transformer can act as a place-holder in a stack, so that the stack has the correct dimensionality.
    """
    def __init__(self, lanes):
        """Initializes the pass-thru.
        
        lanes -- the number of dimensions the pass-thru will pass.
        """
        self.lanes = lanes
        self.dimensions = self.calculateDimensions()
    
    def forward(self, forwardState):
        """Transform in the forward direction.
        
        forwardState -- a single value or list-formatted array containing the input state of the transformer.
        """
        return forwardState
    
    def reverse(self, reverseState):
        """Transform in the reverse direction.
        
        reverseState -- a single value or list-formatted array containing the output state of the transformer.
        """
        return reverseState
    
    def calculateDimensions(self):
        """Calculates and returns the dimensions of the pass-thru.
        
        The dimensions of the pass-thru equals the number of lanes for both the inputs and the outputs.
        """
        return (self.lanes, self.lanes)
        

#--- TRANSFORMER CONTAINERS ---
class chain(transformer):
    """A serial chain of transformer elements."""
    
    def __init__(self, *transformers):
        """Initializes a new transformer chain.
        
        *transformers -- a series of transformer elements, provided as positional arguments in the forward direction.
        """
        self.transformChain = transformers
        self.dimensions = self.calculateDimensions()

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
    
    def calculateDimensions(self):
        """Determines and returns the input and output dimensions of the transformer chain.
        
        The dimensionality of the transformer is defined as the number of degrees of freedom it accepts as inputs and that it
        provides as outputs. Note that this method overrides transformer.calculateDimensions.
        
        returns dimensions as a tuple in the format (outputDimension, inputDimension), where:
            outputDimension -- the number of degrees of freedom of the transformer output
            inputDimension -- the number of degrees of freedom of the transformer input
        """
        outputDimension = self.transformChain[-1].getSize()[0]
        inputDimension = self.transformChain[0].getSize()[1]
        return (outputDimension, inputDimension)


class stack(transformer):
    """A parallel stack of transformers."""
    
    def __init__(self, *transformers):
        """Initializes a new transformer stack.
        
        *transformers -- a parallel set of stacked transformers, provided in sequence from the 0th to Nth dimension.
        """
        self.transformerStack = transformers
        self.dimensions = self.calculateDimensions()


    def forward(self, forwardState):
        """Tranforms from an input state of the tranformer stack to the corresponding output state.
        
        forwardState -- the forward-going input state of the transformer stack.
        
        Transformation is accomplished by expanding the input state into chunks sized for each transformer in the stack.
        
        Note that this function over-rides its base class transformer.forward() function.
        """
        
        if not isinstance(forwardState, list): #if the forwardState is not provided as a list-formatted array, wrap it.
            forwardState = [forwardState]
        
        outputState = [] #initialize output state as an empty list
        for transformerElement in self.transformerStack:
            inputDimension = transformerElement.getSize()[1]
            if len(forwardState)>= inputDimension: #make sure there's enough input dimensions remaining
                
                if inputDimension == 1: #single-axis, so feed with dFloat rather than list.
                    forwardSubState = forwardState[0] #feed first value of forwardState
                    forwardState = forwardState[1:] #forwardState gets first value stripped
                    outputSubState = transformerElement.forward(forwardSubState) #perform transform to get output segment state
                else: #multi-axis, feed with a list
                    forwardSubState = forwardState[0:inputDimension]
                    forwardState = forwardState[inputDimension:]
                    outputSubState = transformerElement.forward(forwardSubState)
                
                if not isinstance(outputSubState, list): #output state is not a list, so wrap
                    outputState += [outputSubState]
                else:
                    outputState += outputSubState 

            else:
                utilities.notice(self, "Cannot perform transform because dimension of forward state is less than input dimension of transformer.")
                raise errors.MechanismError("Encountered dimensionality mismatch while attempting transform.")                
        
        if len(forwardState) == 0: 
            if len(outputState) == 1: 
                return outputState[0] #single element, so strip away list
            else: 
                return outputState 
        else: #uh oh! some input is left over
            utilities.notice(self, "Cannot perform transform because dimension of forward state is greater than input dimension of transformer.")
            raise errors.MechanismError("Encountered dimensionality mismatch while attempting transform.")               


    def reverse(self, outputState):
        """Tranforms from an output state of the tranformer chain to the corresponding input state.
        
        outputState -- the reverse-going output state of the transformer stack.
        
        Transformation is accomplished by expanding the output state into chunks sized for each transformer in the stack.
        
        Note that this function over-rides its base class transformer.reverse() function.
        """
        if not isinstance(outputState, list): #if the forwardState is not provided as a list-formatted array, wrap it.
            outputState = [outputState]
        
        inputState = [] #initialize input state as an empty list
        for transformerElement in self.transformerStack:
            outputDimension = transformerElement.getSize()[0]
            if len(outputState)>= outputDimension: #make sure there's enough input dimensions remaining
                
                if outputDimension == 1: #single-axis, so feed with dFloat rather than list.
                    outputSubState = outputState[0] #feed first value of outputState
                    outputState = outputState[1:] #outputState gets first value stripped
                    inputSubState = transformerElement.reverse(outputSubState) #perform transform to get input segment state
                else: #multi-axis, feed with a list
                    outputSubState = outputState[0:outputDimension]
                    outputState = outputState[outputDimension:]
                    inputSubState = transformerElement.reverse(outputSubState)
                
                if not isinstance(inputSubState, list): #input state is not a list, so wrap
                    inputState += [inputSubState]
                else:
                    inputState += inputSubState 

            else:
                utilities.notice(self, "Cannot perform transform because dimension of forward state is less than input dimension of transformer.")
                raise errors.MechanismError("Encountered dimensionality mismatch while attempting transform.")                
        
        if len(outputState) == 0: 
            if len(inputState) == 1: 
                return inputState[0] #single element, so strip away list
            else: 
                return inputState 
        else: #uh oh! some input is left over
            utilities.notice(self, "Cannot perform transform because dimension of forward state is greater than input dimension of transformer.")
            raise errors.MechanismError("Encountered dimensionality mismatch while attempting transform.")               
          
          
    def calculateDimensions(self):
        """Determines and returns the input and output dimensions of the transformer stack.
        
        The dimensionality of the transformer is defined as the number of degrees of freedom it accepts as inputs and that it
        provides as outputs. Note that this method overrides transformer.calculateDimensions. Dimensionality is calculated
        by summing the dimensions of the parallel items in the stack.
        
        returns dimensions as a tuple in the format (outputDimension, inputDimension), where:
            outputDimension -- the number of degrees of freedom of the transformer output
            inputDimension -- the number of degrees of freedom of the transformer input
        """
        inputDimension = 0
        outputDimension = 0
        for transformerElement in self.transformerStack:
            outputSize, inputSize = transformerElement.getSize()
            outputDimension += outputSize
            inputDimension += inputSize
        
        return (outputDimension, inputDimension)


def gang(transformer):
    """Reduces the outputs of multiple single-axis transformers to one dimension.
    
    This object will convert multiple inputs to a single output, and is useful for e.g. machines that rely on multiple 
    linear actuators moving in synchrony to maintain parallelism. This type of arrangement can be found on many varieties
    of hobbyist-grade 3D printers and CNC machines.
    """
    pass
