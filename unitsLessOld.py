# pyGestalt Units Library

"""A set of common measurement units typically associated with numbers.

NOTE: The user should avoid doing substantial math using the dimensional dFloat type defined here.
It is inefficient and is largely intended to keep things straight and avoid unit mistakes when
defining machine kinematics or performing analysis.
"""

from pygestalt import errors, utilities
import math
import copy

class unit(object):
    """The base class for all measurement units."""
    def __init__(self, abbreviation, fullName, baseUnit = None, conversion = None):
        """Generates a new unit type.
        
        abbreviation -- a shorthand abbreviation for the unit, which will show up when printed. E.g. 'mm'.
        fullName -- a full name for the unit, e.g. 'millimeters'.
        baseUnit -- A unit type from which this unit a scalar multiple. For example, if this unit was millimeters, the base unit might be meters.
        conversion -- The conversion factor to get from the base unit to this unit. thisUnit = conversion*baseUnit.
            -- If conversion is None, this will be treated as a base unit.
            -- If conversion is 0, this will be treated as a non-dimensional unit.
        """
        self.abbreviation = abbreviation
        self.fullName = fullName
        self.baseUnit = baseUnit
        self.conversion = conversion
    
    def __call__(self, value = 1.0):
        """Generates a new dFloat with the units of this unit object.
        
        value -- a floating point value for the dimensional number.
        """
        if type(value) == dFloat:
            return dFloat.convert(value, self)
        else:
            return dFloat(value, {self:1})
    
    def __mul__(self, value):
        """Left multiply for units.
        
        Gets called when a number or unit is directly multiplied by a unit to create a dFloat.
        """
        if type(value) == unit:
            return dFloat(1, {value:1, self:1})
        elif type(value) == dFloat:
            return value*self
        else:
            return dFloat(value, {self:1})        
        
        
    def __rmul__(self, value):
        """Right multiply for units.
        
        Gets called when a number or unit is directly multiplied by a unit to create a dFloat.
        """
        if type(value) == unit:
            return dFloat(1, {value:1, self:1})
        else:
            return dFloat(value, {self:1})
    
    def __rtruediv__(self, value):
        """Right divide for units.
        
        Gets called when a number or unit is directly divided by a unit to create a dFloat.
        """
        
        if type(value) == unit:
            return dFloat(1, {value:1, self:-1})
        else:
            return dFloat(value, {self:-1})

    def __truediv__(self, value):
        """Divide for units.
        
        Gets called when a unit is directly divided by a unit or number to create a dFloat.
        """
        
        if type(value) == unit:
            return dFloat(1, {value:-1, self:1})
        elif type(value) == dFloat:
            return dFloat(1, {self:1})/value
        else:
            return dFloat(1.0/value, {self:1})
    
    def __pow__(self, power):
        """Power for units.
        
        Gets called when a unit is brought to a power, to create a dFloat."""
        return dFloat(1, {self:power})


class unitDictionary(dict):
    """A dictionary subclass used to store units and their powers."""
    def __init__(self, inputDictionary = {}):
        """Initialization function for unit dictionary.
        
        inputDictionary -- a seed dictionary in the form {unitObject:unitPower,...}
        """
        dict.__init__(self, inputDictionary)
    
    def __mul__(self, inputUnitDict):
        """Overrides multiplication to mix units into the dictionary.
        
        inputUnitDict -- a set of units either of unitDictionary type or in the same format: {unitObject:unitPower,...}
        """
        outputUnitDict = copy.copy(self) #work on a copy of self
        
        if type(inputUnitDict) == unitDictionary or type(inputUnitDict) == dict: #make sure that input is compatible
            for thisUnit in inputUnitDict: #iterate over keys in the input dictionary
                if thisUnit in outputUnitDict: #unit already exists in self
                    outputUnitDict.update({thisUnit: outputUnitDict[thisUnit] + inputUnitDict[thisUnit]}) #add powers to units
                    if outputUnitDict[thisUnit] == 0: outputUnitDict.pop(thisUnit) #if resulting power is 0, remove unit
                else:
                    outputUnitDict.update({thisUnit: inputUnitDict[thisUnit]}) #add new unit to dictionary
        else:
            raise errors.UnitError("Cannot make new unit dictionary using provided input")
        
        return outputUnitDict
    
    def __truediv__(self, inputUnitDict):
        """Overrides division to mix units into the dictionary.
        
        inputUnitDict -- a set of units of unitDictionary type or in the same format {unitObject:unitPower,...}
        """
        outputUnitDict = copy.copy(self) #work on a copy of self
        
        if type(inputUnitDict) == unitDictionary or type(inputUnitDict) == dict: #make sure that input is compatible
            for thisUnit in inputUnitDict: #iterate over keys in the input dictionary
                if thisUnit in outputUnitDict: #unit already exists in self
                    outputUnitDict.update({thisUnit: outputUnitDict[thisUnit] - inputUnitDict[thisUnit]}) #add powers to units
                    if outputUnitDict[thisUnit] == 0: outputUnitDict.pop(thisUnit) #if resulting power is 0, remove unit
                else:
                    outputUnitDict.update({thisUnit: -inputUnitDict[thisUnit]}) #add new unit to dictionary
        
        return outputUnitDict  
    
    def __rtruediv__(self, other):
        """Overrides right-hand division. This is only used to invert units.
        other -- whatever the left-hand multiplier is. Doesn't matter as it doesn't get used.
        """
        outputUnitDict = copy.copy(self) #work on a copy of self
        
        for thisUnit in outputUnitDict: #iterate over keys in the output dictionary
            outputUnitDict.update({thisUnit:-outputUnitDict[thisUnit]})
        
        return outputUnitDict
    
    def __pow__(self, power):
        """Overrides power operator.
        
        power -- the power to which to raise the units."""
        
        outputUnitDict = copy.copy(self) #work on a copy of self
        
        for thisUnit in outputUnitDict: #iterate over keys in the output dictionary
            outputUnitDict.update({thisUnit: power * outputUnitDict[thisUnit]})
            
        return outputUnitDict
               

    def __str__(self):
        """String representation of the unit dictionary."""
        numeratorUnitList = [unitPower for unitPower in self if self[unitPower] > 0]
        denominatorUnitList = [unitPower for unitPower in self if self[unitPower] < 0]
         
        returnString = '' #this is the seed of the return string that will be built upon
         
        #fill in numerator string if no units are in the numerator
        if numeratorUnitList == [] and denominatorUnitList != []:
            returnString += "1"
         
        #fill in numerator string
        for numeratorUnit in numeratorUnitList: #iterate over all units in numerator
            if self[numeratorUnit] > 1: #more than to the first power
                returnString += numeratorUnit.abbreviation + '^' + str(self[numeratorUnit]) + '*'
            else:
                returnString += numeratorUnit.abbreviation + '*'
         
        if numeratorUnitList != []: returnString = returnString[:-1] #remove trailing *
         
        if denominatorUnitList != []: returnString += '/' #add trailing /
         
        for denominatorUnit in denominatorUnitList: #iterate over all units in denominator
            if self[denominatorUnit] < -1: #more than to the first power
                returnString += denominatorUnit.abbreviation + '^' + str(-self[denominatorUnit]) + '*'
            else:
                returnString += denominatorUnit.abbreviation + '*'
         
        if denominatorUnitList != []: returnString = returnString[:-1] #remove trailing *
         
        return returnString


class dFloat(float):
    """A dimensional floating-point number, i.e. a float with units."""
    
    def __new__(self, value, units = {}):
        """Constructor for dFloat that overrides float.__new__
        
        value -- the value of the floating point number.
        units -- a unitDictionary specifying the units for the new dFloat
        """
        return float.__new__(self, value)
    
    def __init__(self, value, units = {}):
        """Initializes the dFloat.
        
        units -- a dictionary containing key pairs of {unitObject: power} for all units
        """
        
        self.units = unitDictionary(units)
    
    def __call__(self, value):
        """A shortcut for creating a new dFloat with the same units as the called dFloat."""
        return dFloat(value, self.units)

    
    def __str__(self):
        """String representation of the dFloat number"""
        
        return str(float(self)) + ' ' + str(self.units)
    
    def baseUnits(self):
        return reduceToBaseUnits(self)
    
    def convert(self, targetUnits):
        return convertToUnits(self, targetUnits)
    
    #--- OVERRIDE MATH FUNCTIONS ---
    def __add__(self, other):
        """Overrides addition.
        
        other -- the right-hand number to add
        
        A unit check will be performed if right-hand operand is of type dFloat. Otherwise the units
        of this dFloat will be passed along into the result.
        """
        value = float(self) + float(other) #perform numerical addition
        units = unitDictionary(self.units) #make a copy of unit dictionary
        if type(other) == dFloat:
            if self.units != other.units: #check to make sure units match
                raise errors.UnitError("addition operand units don't match")
        return dFloat(value, units)
    
    def __radd__(self, other):
        """Overrides right-handed addition.
        
        other -- the left-hand number to add.
        
        The units of this dFloat will be passed along into the result.
        """
        value = float(self) + float(other)
        units = unitDictionary(self.units)
        return dFloat(value, units)
    
    def __sub__(self, other):
        """Overrides subtraction.
        
        other -- the right-hand number to subract.

        A unit check will be performed if right-hand operand is of type dFloat. Otherwise the units
        of this dFloat will be passed along into the result.
        """
        value = float(self) - float(other) #perform numerical addition
        units = unitDictionary(self.units) #make a copy of unit dictionary
        if type(other) == dFloat:
            if self.units != other.units: #check to make sure units match
                raise errors.UnitError("addition operand units don't match")
        return dFloat(value, units)        
    
    def __rsub__(self, other):
        """Overrides right-handed subtraction.
        
        other -- the left-hand number to subtract.
        
        The units of this dFloat will be passed along into the result.
        """
        value = float(other) - float(self)
        units = unitDictionary(self.units)
        return dFloat(value, units)
    
    def __neg__(self):
        """Overrides negation."""
        value = -float(self)
        units = unitDictionary(self.units)
        return dFloat(value, units)
    
    def __abs__(self):
        """Overrides absolute value."""
        value = abs(float(self))
        units = unitDictionary(self.units)
        return dFloat(value, units)
        
        
    def __mul__(self, other):
        """Overrides left-hand multiplication.
        
        other -- right-hand number to be multiplied.
        """
        if type(other) != unit: #not multiplying by a generic unit
            value = float(self) * float(other) #perform numerical multiplication
            if type(other) == dFloat: #mix in units of other operand units
                newUnits = self.units*other.units
            else:
                newUnits = self.units
            return dFloat(value, newUnits)
        else:
            newUnits = self.units * {other:1}
            return dFloat(float(self), newUnits)
    
    def __rmul__(self, other):
        """Overrides right-hand multiplication.
        
        other -- left-hand number to be multiplied.
        
        Note that this will only be called if the left-hand number is not a dFloat.
        """
        if type(other) != unit: #not multiplying by a generic unit
            value = float(other) * float(self)
            return dFloat(value, self.units)
        else:
            newUnits = {other:1} * self.units
            return dFloat(value, newUnits)
    
    def __truediv__(self, other):
        """Overrides left-hand division.
        
        other -- the right-hand number to be divided by.
        """
        if type(other) != unit: #not dividing by a generic unit
            value = float(self)/ float(other) #perform numerical division
            if type(other) == dFloat: #mix in inverse of right-hand operand units
                newUnits = self.units / other.units
            else:
                newUnits = self.units
            return dFloat(value, newUnits)
        else:
            newUnits = self.units / {other:1}
            return dFloat(float(self), newUnits)
    
    def __rtruediv__(self, other):
        """Overrides right-hand division.
        
        other -- the left-hand number to divide.
        
        Note that this will only be called if the left-hand number is not a dFloat.
        """
        if type(other) != unit: #not dividing by a generic unit
            value = float(other) / float(self)
            return dFloat(value, 1/self.units)   #inverted unit powers
        else:
            newUnits = (1 / self.units) * {other:1}
    
    def __pow__(self, other):
        """Overrides exponential.
        
        other -- the power to raise this value to.
        """
        value = float(self)**float(other)
        newUnits = self.units ** other
        return dFloat(value, newUnits)

#-- CONVERSION FUNCTIONS --
def getBaseUnits(derivedUnits):
    """Determines the base unit and scaling factor of a provided unit.
    
    Note that this function runs recursively until a base unit has been found
    
    Returns baseUnit, conversion, where:
        baseUnit -- the base unit of the provided derived units
        conversion -- the scaling factor to go from the base units to the provided derived units. derivedUnit = conversion*baseUnit
    """
    if type(derivedUnits.baseUnit) == unit: #it's a derived unit!
        baseUnit, conversion = getBaseUnits(derivedUnits.baseUnit)
        return baseUnit, derivedUnits.conversion*conversion
    else:
        return derivedUnits, 1.0

def reduceToBaseUnits(sourceNumber):
    """Reduces a dFloat into an equivalent in base units.
    
    sourceNumber -- a dFloat to be reduced.
    
    returns an equivalent dFloat whose units are the base units. 
    """
    if type(sourceNumber) != dFloat:
        raise errors.UnitError("Unable to reduce units. Must provide source number as a dFloat.")
        return False
    else:
        value = float(sourceNumber)
        units = sourceNumber.units #unitDictionary
        baseUnits = unitDictionary()
        for thisUnit in units: #iterate over units in unit dictionary
            baseUnit, conversionFactor = getBaseUnits(thisUnit)
            power = units[thisUnit] #the power to which the unit is raised
            baseUnits.update({baseUnit:power})
            value = value/(conversionFactor**power)
        return dFloat(value, baseUnits)      

def unitsAreEqual(number1, number2):
    """Returns True if both provided numbers have equal units.
    
    number1, number2 -- dFloat numbers or unitDictionaries
    
    Note that this algorithm both checks to see if the unit dictionaries are identical while also taking into account
    non-dimensional units such as radians. It DOES NOT reduce to base units first, so mm != m.
    """
    
    unitDict1 = copy.copy(number1.units) #make copies of dictionaries so don't mess with them
    unitDict2 = copy.copy(number2.units)
    
    for units1 in unitDict1: #iterate over all units in the first unit dictionary
        units1Power = unitDict1[units1]
        units2Power = unitDict2.pop(units1, False) #Retrieve unit powers. Returns False if units1 is not in unitDict2
    
        if units1.baseUnit == 0: #units1 is dimensionless, so continue to next iteration
            continue
        if units2Power == False: #units1 is inot in unitsDict2!
            utilities.debugNotice('units.unitsAreEqual', 'units', "Dimensionality mismatch: units "+ units1.abbreviation + " not in both numbers")
            return False
        if units1Power != units2Power: #powers are different
            utilities.debugNotice('units.unitsAreEqual', 'units', "Dimensionality mismatch: " + units1.abbreviation + "^"+str(units1Power) + " != " + units1.abbreviation + "^"+str(units2Power))
            return False
        else:
            continue #this set of units matches
    
    #at this point, unitDict1 has been fully iterated thru. Still need to check that all remaining units in unitDict2 are dimensionless
    for units2 in unitDict2:
        if units2.baseUnit == 0:
            utilities.notice('units.unitsAreEqual', "WARNING: Non-dimensional units do not match. Assuming unit type " + units2.fullName.upper())
            continue
        else:
            utilities.debugNotice('units.unitsAreEqual', 'units', "Dimensionality "+ units2.abbreviation + " not present in both numbers")
            return False
    
    return True #if reached this point, unit dictionaries match

def unitsAreReciprocals(number1, number2):
    """Returns True if both provided numbers have equivalent reciprocal units.
    
    number1, number2 -- dFloat numbers or unitDictionaries
    
    Note that this algorithm both checks to see if the unit dictionaries are reciprocals while also taking into account
    non-dimensional units such as radians. It DOES NOT reduce to base units first, so mm != m.
    """

    unitDict1 = copy.copy(number1.units) #make copies of dictionaries so don't mess with them
    unitDict2 = copy.copy(number2.units)
    
    for units1 in unitDict1: #iterate over all units in the first unit dictionary
        units1Power = unitDict1[units1]
        units2Power = unitDict2.pop(units1, False) #Retrieve unit powers. Returns False if units1 is not in unitDict2
    
        if units1.baseUnit == 0: #units1 is dimensionless, so continue to next iteration
            continue
        if units2Power == False: #units1 is not in unitsDict2!
            utilities.debugNotice('units.unitsAreReciprocals', 'units', "Dimensionality mismatch: units "+ units1.abbreviation + " not in both numbers")
            return False
        if units1Power != -units2Power: #powers are not reciprocals
            utilities.debugNotice('units.unitsAreReciprocals', 'units', "Dimensionality mismatch: " + units1.abbreviation + "^"+str(units1Power) + " != " + units1.abbreviation + "^-"+str(units2Power))
            return False
        else:
            continue #this set of units matches
    
    #at this point, unitDict1 has been fully iterated thru. Still need to check that all remaining units in unitDict2 are dimensionless
    for units2 in unitDict2:
        if units2.baseUnit == 0:
            utilities.notice('units.unitsAreReciprocals', "WARNING: Non-dimensional units do not match. Assuming unit type " + units2.fullName.upper())
            continue
        else:
            utilities.debugNotice('units.unitsAreReciprocals', 'units', "Dimensionality "+ units2.abbreviation + " not present in both numbers")
            return False
    
    return True #if reached this point, unit dictionaries match    

def getUnitEquivalency(number1, number2):
    """Returns the equivalency of the units of two input numbers.

    number1, number2 -- dFloat numbers or unitDictionaries
    
    Equivalency is defined as numbers whose BASE units are either equal or reciprocals.
    
    Returns the power of the equivalency (1 or -1), or 0 if the units are not equivalent
    """       
    if unitsAreEqual(reduceToBaseUnits(number1), reduceToBaseUnits(number2)):
        return 1
    elif unitsAreReciprocals(reduceToBaseUnits(number1), reduceToBaseUnits(number2)):
        return -1
    else:
        return 0
    
    
def hasUnits(sourceNumber, unitsToCheck, checkEquivalents = True):
    """ Checks whether a dFloat's unit dictionary contains a particular unit type.
    
    sourceNumber -- the number whose units are to be checked
    unitsToCheck -- a unit type whose presence is to be checked in the source number
    checkEquivalents -- unless explicitly provided as False, this function will return True if an equivalent unit to unitsToCheck
                        is found to be present in the source number.
    """
    if checkEquivalents: #reduce everything to base units
        sourceUnits = {getBaseUnits(unit)[0]:sourceNumber.units[unit] for unit in sourceNumber.units} #get dictionary of base units
        targetUnit = getBaseUnits(unitsToCheck)[0]
    else: #only accept literally equivalent units
        sourceUnits = sourceNumber.units
        targetUnit = unitsToCheck
    return (targetUnit in sourceUnits)
    

def convertToUnits(sourceNumber, targetUnits, strict = False):
    """Converts a number into target units if possible.
    
    sourceNumber -- a dFloat number to be converted
    targetUnits -- either a dFloat, unitDictionary, or unit
    strict -- if False, will allow conversion between reciprocal numbers.
    
    returns a dFloat in the target units, or raises an exception if units mis-match.
    """
    
    sourceBaseNumber = reduceToBaseUnits(sourceNumber)

    if type(targetUnits) == unit: #target units are provided as a single unit type
        targetNumber = dFloat(1,{targetUnits:1})
    elif type(targetUnits) == unitDictionary: #target units are provided as a unit dictionary
        targetNumber = dFloat(1, targetUnits)
    elif type(targetUnits) == dFloat: #target units are provided as a dFloat
        targetNumber = targetUnits
    else: #target units are not provided as valid
        raise errors.UnitError("Unable to convert. " + str(targetUnits) + " is not a valid unit!")
        return False
    
    targetBaseNumber = reduceToBaseUnits(targetNumber) #reduce target units to base. This conveniently includes the multiplication factor
    
    unitEquivalency = getUnitEquivalency(sourceBaseNumber, targetBaseNumber) #1 if equivalent, -1 if reciprocals, or 0 if not equivalent
    
    conversionFactor = float(targetBaseNumber)**unitEquivalency
    convertedNumber = dFloat((float(sourceBaseNumber)/conversionFactor)**unitEquivalency, targetNumber.units)
    
    if (unitEquivalency == 1) or (not strict and unitEquivalency == -1):
        return convertedNumber
    else:
        raise errors.UnitError("Unable to convert from "+ str(sourceNumber.units) + " to " + str(targetNumber.units) + ". Dimensionality mismatch.")        
    
def applyDefaultUnits(value, defaultUnits):
    """Applies default units to a value if not already a dFloat.
    
    value -- the value to be checked. If a dFloat object is provided, no change will be performed
    defaultUnits -- the unit type to be applied
    
    Returns a dFloat, either as provided, or with default units.
    """
    if type(value) == dFloat:
        return value #already a dFloat, no need to convert
    else:
        return defaultUnits*value #multiplying is the safest way to do this, because it works with compound units (e.g. px/inch)

def getAbbreviation(value):
    """Returns the abbreviation string for an input unit or dFloat."""
    if type(value) == unit:
        return value.abbreviation
    elif type(value) == dFloat:
        return str(value.units)
    else:
        return None

#-- STANDARD UNITS --

# distance
m = unit('m', 'meter') #meters are a base unit of distance
cm = unit('cm', 'centimeter', m, 100.0)
mm = unit('mm', 'millimeter', m, 1000.0)
inch = unit('in', 'inch', mm, 1.0/25.4)
ft = unit('ft', 'feet', inch, 1.0/12.0)
yd = unit('yd', 'yard', inch, 1.0/36.0)

# angle
rad = unit('rad', 'radian', 0) #radians are base unit of angle, and are dimensionless
deg = unit('deg', 'degree', rad, 180.0 / math.pi)
rev = unit('rev', 'revolution', rad, 1.0/(2.0*math.pi))

# time
s = unit('s', 'second') #seconds are base unit of time
min = unit('min', 'minute', s, 1.0/60.0)
hr = unit('hr', 'hour', s, 1.0/3600.0)

# mass
kg = unit('kg', 'kilogram') #kilograms are base unit of mass
g = unit('g', 'gram', kg, 1000.0)
oz = unit('oz', 'ounce', g, 0.035274)
lb = unit('lb', 'pound', oz, 1.0/16.0)

# force
N = unit('N', 'newton') #newtons are the base unit of force. Eventually need to build in a derived unit system to convert into SI base units.
kgf = unit('kgf', 'kilogram force', N, 1.0/9.80665)
gf = unit('gf', 'gram force', kgf, 1000.0)
ozf = unit('ozf', 'ounce force', gf, 0.035274)
lbf = unit('lbf', 'pound force', ozf, 1.0/16.0)

# electrical
V = unit('V', 'volt')
A = unit('A', 'amp')
# pseudo-units
# these units are just to make it easier to keep track of transformations thru the system, and are not necessarily SI units
step = unit('step', 'step') #steps are base units
px = unit('px', 'pixels') #pixels are base units