#   pyGestalt Units Module

"""A set of common measurement units typically associated with numbers.

NOTE: The user should avoid doing substantial math using the dimensional dFloat type defined here.
It is very inefficient and is largely intended to keep things straight and avoid unit mistakes when
defining machine kinematics or performing analysis.
"""

import errors
import math

class unitDict(dict):
    """A dictionary sublcass used to store units and their powers."""
        
    def update(self, other):
        """Overrides dict.update to modify powers if unit is already present.
        
        other -- a dictionary of {unit:power} mappings to be used in updating this dictionary
        """
        for key in other: #increment over keys in dictionary
            if key in self:
                dict.update(self, {key: self[key]+other[key]}) #unit already is in dictionary, so add powers
            else:
                dict.update(self, {key: other[key]})
        self.reduce()
        
    def reduce(self):
        """Removes any units whose power is 0.
        
        Ruthless, no?
        """
        hitList = filter(lambda unitPower: self[unitPower] == 0, self)
        for thisUnit in hitList:
            self.pop(thisUnit)
    
    def __neg__(self):
        """Overrides the negative operator to invert the powers of the contained units."""
        newUnitDict = unitDict(self)    #create new copy
        for key in newUnitDict:  #invert powers of all units
            newUnitDict[key] *= -1
        return newUnitDict
    
    def __mul__(self, other):
        """Overrides the multiplication operator to return units whose powers have been multiplied by other."""
        
        newUnitDict = unitDict(self)
        for key in newUnitDict:
            newUnitDict[key] *= other
        return newUnitDict
    
    def __init__(self, value):
        """Initialization function for unit dictionary"""
        dict.__init__(self, value)
        self.reduce()
         
    def __str__(self):
        """String representation of the unit dictionary."""
        numeratorUnitList = filter(lambda unitPower: self[unitPower] > 0, self)
        denominatorUnitList = filter(lambda unitPower: self[unitPower] < 0, self)
         
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

class unit(object):
    """The base class for all measurement units."""
    
    def __init__(self, dimension, conversion, abbreviation, fullName, derivedUnits = {}):
        """Generates a new unit type.
        
        abbreviation -- the abbreviation to be used when printing the unit.
        fullName -- the full name of the unit
        derivedUnits -- a dictionary containing key pairs of {unitObject: power} for all units in the numerator from which this unit is derived
        """
        
        self.dimension = dimension #the dimension of the unit
        self.conversion = conversion #the conversion factor FROM BASE UNITS INTO THIS UNIT
        self.abbreviation = abbreviation
        self.fullName = fullName
        
        #keep track of base units for unit conversion and display purposes
        if derivedUnits != {}:
            self.baseUnits = unitDict(derivedUnits) #base units come from derived units
        else:
            self.baseUnits = unitDict({self, 1}) #base units are simply self
        
        dimension.addUnit(self, conversion) #adds this unit to the dimension object
        
    def __call__(self, value):
        """Generates a new dFloat with the units of this unit object.
        
        value -- a floating point value for the dimensional number.
        """
        
        if self.derivedUnits != {}:    #this is a derived unit
            return dFloat(value, self.derivedUnits)
        else:   #not a derived unit, return dFloat with this as unit in numerator
            return dFloat(value, {self:1})

class dimension(object):
    """This class defines a dimension such as distance or time."""
    def __init__(self):
        self.associatedUnits = {} #dictionary keeps track of which units are associated with this dimension
                                  # conversion factors are stored as {unitObject: conversion}
                                  # conversion is going from base units to associated unit
    
    def addUnit(self, unit, conversion):
        self.associatedUnits.update({unit:conversion})
        
    def convert(self, sourceUnit, targetUnit):
        """Finds the scaling factor between the source and target units
        
        Returns the scaling factor as a dFloat with target units, or False if no conversion is found.
        """
        if sourceUnit in self.associatedUnits:
            baseFactor = self.associatedUnits[sourceUnit] #this is the number of source units in the base unit
        else:
            raise errors.UnitConversionError("Source unit not found in dimension")
            return False #source units not found

        if targetUnit in self.associatedUnits:
            targetFactor = self.associatedUnits[targetUnit]
        else:
            raise errors.unitConversionError("Target unit not found in dimension")
            return False
        
        value = float(baseFactor)/float(targetFactor)
        units = unitDict({targetUnit:1})
        return dFloat(value, units)

def convert(number, targetUnits):
    """Attempts to convert a dimensional number into target units.
    
    number -- a dFloat to be converted.
    targetUnits -- a unit type into which the dFloat should be converted.
    
    returns a dFloat in target units, or None if conversion isn't possible.
    """
    sourceUnits = number.units
    targetUnits = targetUnits.baseUnits
    
    
    
class dFloat(float):
    """A dimensional floating-point number, i.e. a float with units."""
    
    def __new__(self, value, units = {}):
        """Constructor for dFloat that overrides float.__new__
        
        value -- the value of the floating point number.
        numeratorUnits -- a dictionary containing key pairs of {unitObject: power} for all units in the numerator
        denominatorUnits -- a dictionary containing key pairs of {unitObject: power} for all units in the denominator
        """
        return float.__new__(self, value)
    
    def __init__(self, value, units = {}):
        """Initializes the dFloat.
        
        units -- a dictionary containing key pairs of {unitObject: power} for all units
        """
        
        self.units = unitDict(units)
            
    def __str__(self):
        """String representation of the dFloat number"""
        
        return str(float(self)) + ' ' + str(self.units)
    
    #--- OVERRIDE MATH FUNCTIONS ---
    def __add__(self, other):
        """Overrides addition.
        
        other -- the right-hand number to add
        
        A unit check will be performed if right-hand operand is of type dFloat. Otherwise the units
        of this dFloat will be passed along into the result.
        """
        value = float(self) + float(other) #perform numerical addition
        units = unitDict(self.units) #make a copy of unit dictionary
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
        units = unitDict(self.units)
        return dFloat(value, units)
    
    def __sub__(self, other):
        """Overrides subtraction.
        
        other -- the right-hand number to subract.

        A unit check will be performed if right-hand operand is of type dFloat. Otherwise the units
        of this dFloat will be passed along into the result.
        """
        value = float(self) - float(other) #perform numerical addition
        units = unitDict(self.units) #make a copy of unit dictionary
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
        units = unitDict(self.units)
        return dFloat(value, units)
    
    def __mul__(self, other):
        """Overrides left-hand multiplication.
        
        other -- right-hand number to be multiplied.
        """
        value = float(self) * float(other) #perform numerical multiplication
        units = unitDict(self.units) #copy units dictionary
        if type(other) == dFloat: #mix in units of other operand units
            units.update(other.units)
        return dFloat(value, units)
    
    def __rmul__(self, other):
        """Overrides right-hand multiplication.
        
        other -- left-hand number to be multiplied.
        
        Note that this will only be called if the left-hand number is not a dFloat.
        """
        value = float(other) * float(self)
        return dFloat(value, self.units)
    
    def __div__(self, other):
        """Overrides left-hand division.
        
        other -- the right-hand number to be divided by.
        """
        value = float(self)/ float(other) #perform numerical division
        units = unitDict(self.units) #copy units dictionary
        if type(other) == dFloat: #mix in inverse of right-hand operand units
            units.update(-other.units)
        return dFloat(value, units)
    
    def __rdiv__(self, other):
        """Overrides right-hand division.
        
        other -- the left-hand number to divide.
        
        Note that this will only be called if the left-hand number is not a dFloat.
        """
        value = float(other) / float(self)
        return dFloat(value, -self.units)   #inverted unit powers
    
    def __pow__(self, other):
        """Overrides exponential.
        
        other -- the power to raise this value to.
        """
        value = float(self)**float(other)
        units = unitDict(self.units * other)
        return dFloat(value, units)
    

#--- DEFINE DIMENSIONS HERE ---
distance = dimension() #base unit is meters
angle = dimension() #base unit is radians
time = dimension() #base unit is seconds
force = dimension() #base unit is newtons
mass = dimension() #base unit is kg

#--- DEFINE UNITS HERE ---

# distance
m = unit(distance, 1.0, 'm', 'meters') #meters are the base units of distance
mm = unit(distance, 0.001, 'mm', 'millimeters')
cm = unit(distance, 0.01, 'cm', 'centimeters')
inches = unit(distance, 0.0254, 'in', 'inches')

# angle
rad = unit(angle, 1.0, 'rad', 'radians') #radians are the base units of angle
deg = unit(angle, (2.0*math.pi)/360.0, 'deg', 'degrees')
rev = unit(angle, 2.0*math.pi, 'rev', 'revolutions')

# time
s = unit(time, 1.0, 's', 'seconds') #seconds are the base units of time
min = unit(time, 60.0, 'min', 'minutes')
h = unit(time, 3600.0, 'h', 'hours')

# force
N = unit(force, 1.0, 'N', 'newtons') #newtons are the base unit of force
kgf = unit(force, 9.806, 'kgf', 'kilograms force')
ozf = unit(force, 9.806/35.274, 'oz', 'ounces')
