#   pyGestalt Units Module

"""A set of common measurement units typically associated with numbers.

NOTE: The user should avoid doing substantial math using the dimensional dFloat type defined here.
It is very inefficient and is largely intended to keep things straight and avoid unit mistakes when
defining machine kinematics or performing analysis.
"""

import errors

class unitDict(dict):
    """A dictionary sublcass used to store units and their powers."""
    
    def update(self, other):
        """Overrides dict.update to increment powers if unit is already present.
        
        other -- a dictionary of {unit:power} mappings to be used in updating this dictionary
        """
        for key in other: #increment over keys in dictionary
            if key in self:
                dict.update(self, {key: self[key]+other[key]}) #unit already is in dictionary, so add powers
            else:
                dict.update(self, {key: other[key]})
    
    def __str__(self):
        """String representation of the unit dictionary."""
        baseString = '' #growing string
        for thisUnit in self:
            if self[thisUnit] > 1: #more than to the first power
                baseString += thisUnit.abbreviation + '^' + str(self[thisUnit]) + '*'
            else:
                baseString += thisUnit.abbreviation + '*'
        return baseString[:-1] #don't want to return the trailing multiplication


class unit(object):
    """The base class for all measurement units."""
    
    def __init__(self, abbreviation, fullName, numeratorUnits = {}, denominatorUnits = {}):
        """Generates a new unit type.
        
        abbreviation -- the abbreviation to be used when printing the unit.
        fullName -- the full name of the unit
        numeratorUnits -- a dictionary containing key pairs of {unitObject: power} for all units in the numerator from which this unit is derived
        denominatorUnits -- a dictionary containing key pairs of {unitObject: power} for all units in the denominator from which this unit is derived
        """
        self.abbreviation = abbreviation
        self.fullName = fullName
        self.numeratorUnits = {}
        self.denominatorUnits = {}
        
    def __call__(self, value):
        """Generates a new dFloat with the units of this unit object.
        
        value -- a floating point value for the dimensional number.
        
        If this unit is not derived from other units, i.e. numeratorUnits and denominatorUnits are empty,
        then the dFloat will be created with this unit in its numerator. Otherwise the dFloat will get
        the numerator and demoniminator of self. This is done so that if the dFloat has other arithmatic
        done to it, its base units remain fundamental for conversion purposes.
        """
        
        numeratorUnits = {}
        denominatorUnits = {}
        numeratorUnits.update(self.numeratorUnits)
        denominatorUnits.update(self.denominatorUnits)
        
        if numeratorUnits != {}:    #this is a derived unit
            return dFloat(value, numeratorUnits, denominatorUnits)
        else:   #not a derived unit, return dFloat with this as unit in numerator
            return dFloat(value, {self:1})


class dFloat(float):
    """A dimensional floating-point number, i.e. a float with units."""
    
    def __new__(self, value, numeratorUnits = {}, denominatorUnits = {}):
        """Constructor for dFloat that overrides float.__new__
        
        value -- the value of the floating point number.
        numeratorUnits -- a dictionary containing key pairs of {unitObject: power} for all units in the numerator
        denominatorUnits -- a dictionary containing key pairs of {unitObject: power} for all units in the denominator
        """
        return float.__new__(self, value)
    
    def __init__(self, value, numeratorUnits = {}, denominatorUnits = {}):
        """Initializes the dFloat.
        
        numeratorUnits -- a dictionary containing key pairs of {unitObject: power} for all units in the numerator
        denominatorUnits -- a dictionary containing key pairs of {unitObject: power} for all units in the denominator
        """
        
        #reduce to remove all duplicate units
        for thisUnit in dict(numeratorUnits): #iterate over all numerator units
            if thisUnit in denominatorUnits:
                if numeratorUnits[thisUnit] > denominatorUnits[thisUnit]:
                    numeratorUnits[thisUnit] -= denominatorUnits[thisUnit]
                    denominatorUnits.pop(thisUnit)
                elif numeratorUnits[thisUnit] == denominatorUnits[thisUnit]:
                    numeratorUnits.pop(thisUnit)
                    denominatorUnits.pop(thisUnit)
                else:
                    denominatorUnits[thisUnit]-= numeratorUnits[thisUnit]
                    numeratorUnits.pop(thisUnit)
        
        self.numeratorUnits = unitDict(numeratorUnits)
        self.denominatorUnits = unitDict(denominatorUnits)
            
    def __str__(self):
        """String representation of the dFloat number"""
        
        returnString = ' '
        numeratorLength = len(self.numeratorUnits)
        denominatorLength = len(self.denominatorUnits)
        
        if numeratorLength == 0 and denominatorLength > 0: #no numerator
            returnString += '1'
        elif numeratorLength == 1: #single numerator
            returnString += str(self.numeratorUnits)
        else: #multiple numerators
            if denominatorLength == 0: #no denominator
                returnString += str(self.numeratorUnits)
            else:
                returnString += "(" + str(self.numeratorUnits) + ")"
        
        if denominatorLength == 1:
            returnString += "/" + str(self.denominatorUnits)
        elif denominatorLength > 1:
            returnString += "/(" + str(self.denominatorUnits) + ")"
        
        return str(float(self)) + returnString
    
    def __mul__(self, other):
        """Overrides left-hand multiplication.
        
        other -- right-hand number to be multiplied.
        """
        if type(other) == dFloat:
            value = float(self) * float(other)
            numeratorUnits = unitDict(self.numeratorUnits) #make a copy
            denominatorUnits = unitDict(self.denominatorUnits) #make a copy
            numeratorUnits.update(other.numeratorUnits)
            denominatorUnits.update(other.denominatorUnits)
            return dFloat(value, numeratorUnits, denominatorUnits)
        else:
            return dFloat(float(self)*other, self.numeratorUnits, self.denominatorUnits)
    
    def __rmul__(self, other):
        """Overrides right-hand multiplication.
        
        other -- left-hand number to be multiplied.
        
        Note that this will only be called if the left-hand number is not a dFloat.
        """
        return dFloat(other*float(self), self.numeratorUnits, self.denominatorUnits)
    
    def __div__(self, other):
        """Overrides left-hand division.
        
        other -- right-hand number to be divided by.
        """
        if type(other) == dFloat:
            value = float(self)/float(other)
            numeratorUnits = unitDict(self.numeratorUnits) #make a copy
            denominatorUnits = unitDict(self.denominatorUnits) #make a copy
            numeratorUnits.update(other.denominatorUnits)
            denominatorUnits.update(other.numeratorUnits)
            return dFloat(value, numeratorUnits, denominatorUnits)
        else:
            return dFloat(float(self)/float(other), self.numeratorUnits, self.denominatorUnits)
    
    def __rdiv__(self, other):
        """Overrides right-hand division.
        
        other -- left-hand number to be divided by self.
        
        Note that this will only be called if the left-hand number is not a dFloat.
        """
        return dFloat(other/float(self), self.denominatorUnits, self.numeratorUnits)    #invert numerator and denominator
    
    def __pow__(self, other):
        """Overrides left-hand exponent.
        
        other -- left-hand number to be raised to a particular power.
        """
        if type(other) == dFloat:
            raise errors.UnitError('Unable to use exponent that contains units.')
        else:
            numeratorUnits = unitDict(self.numeratorUnits)
            denominatorUnits = unitDict(self.denominatorUnits)
            
            for thisUnit in numeratorUnits:
                numeratorUnits[thisUnit] *= exponent
            
            return dFloat(float(self)**other, )
    
#--- DEFINE UNITS HERE ---

# distance
mm = unit('mm', 'millimeters')
cm = unit('cm', 'centimeters')
m = unit('m', 'meters')
inches = unit('in', 'inches')

# time
s = unit('s', 'seconds')

# force
N = unit('N', 'newtons')
kgf = unit('kgf', 'kilograms force')
oz = unit('oz', 'ounces')

# angle
rad = unit('rad', 'radians')
deg = unit('deg', 'degrees')