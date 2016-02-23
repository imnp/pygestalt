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
            if self[denominatorUnit] < 1: #more than to the first power
                returnString += denominatorUnit.abbreviation + '^' + str(-self[denominatorUnit]) + '*'
            else:
                returnString += denominatorUnit.abbreviation + '*'
         
        if denominatorUnitList != []: returnString = returnString[:-1] #remove trailing *
         
        return returnString
        
        
        
    

class unit(object):
    """The base class for all measurement units."""
    
    def __init__(self, abbreviation, fullName, derivedUnits = {}):
        """Generates a new unit type.
        
        abbreviation -- the abbreviation to be used when printing the unit.
        fullName -- the full name of the unit
        derivedUnits -- a dictionary containing key pairs of {unitObject: power} for all units in the numerator from which this unit is derived
        """
        self.abbreviation = abbreviation
        self.fullName = fullName
        self.derivedUnits = derivedUnits
        
    def __call__(self, value):
        """Generates a new dFloat with the units of this unit object.
        
        value -- a floating point value for the dimensional number.
        
        If this unit is not derived from other units, i.e. derivedUnits empty,
        then the dFloat will be created with this unit in its numerator. Otherwise the dFloat will get
        the units of self. This is done so that if the dFloat has other arithmatic
        done to it, its base units remain fundamental for conversion purposes.
        """
        
        if self.derivedUnits != {}:    #this is a derived unit
            return dFloat(value, self.derivedUnits)
        else:   #not a derived unit, return dFloat with this as unit in numerator
            return dFloat(value, {self:1})


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