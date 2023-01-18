# pyGestalt Units Library

""" pyGestalt Units Library

Updated January 15th, 2023

This library provides the functionality needed to assign, track, and convert units.

The two basic types are unit and dFloat.
    -- unit is used to represent the dimensionality of a number. Units can be combined into new units via multiplication, division, and raising to a power.
    -- dFloat is a dimensional floating point number, and is based off of the float class.

It is our hope that by investing effort into this library, other important functionality -- such as simulating the performance of machines -- will become
more straightforward and flexible, and less error-prone.

"""

from pygestalt import errors, utilities
import math
import copy

class unit(object):
    """The base class for all measurement units."""

    def __init__(self, abbreviation, fullName, baseUnit = None, conversion = None, compound_unitdict = None):
        """Generates a new unit type.

        The most basic form of initialization for a unit is simply:
            abbreviation -- a shorthand abbreviation for the unit, which will show up when printed. E.g. 'mm'.
            fullName -- a full name for the unit, e.g. 'millimeters'.
        Both of these are mandatory, but in the case of compound units (e.g. mm/s), they may be auto-generated.


        If the unit is a "derived unit," meaning it is based on other units, then the following should be provided:
            baseUnit -- A unit type from which this unit a scalar multiple. For example, if this unit was millimeters, the base unit might be meters.
                        -- If baseUnit is 0, this will be treated as a non-dimensional unit.
            conversion  -- The conversion factor to get from the base unit to this unit. thisUnit = conversion*baseUnit.

        If the unit is a "compound unit," for example mm/s, then the following should be provided:
            compound_unitdict -- the combination of units from which this unit is derived, of type unitdict. E.g. if this unit represents velocity, 
                                compound_unitdict might be {units.m:1, units.s:-1}. Typically this unitdict is not provided by the user, but rather by 
                                operations performed on the units.

        NOTE: At least for now, units can be derived or compound, but never both.
        """

        self.abbreviation = abbreviation
        self.fullName = fullName
        self.baseUnit = baseUnit
        self.conversion = conversion

        if baseUnit and conversion == None: #check that a conversion factor was also provided.
            raise errors.UnitError("No conversion scaling factor was provided between " + abbreviation + " and base unit " + baseUnit.abbreviation)

        if compound_unitdict:
            self.primary_unitdict = compound_unitdict
        else:
            if self.baseUnit == 0: #dimensionless
                self.primary_unitdict = unitdict({self:1})
            else:
                self.primary_unitdict = unitdict({self:1})

    def __repr__(self):
        if self.isDerivedUnit():
            return self.fullName + " (" + self.abbreviation + ") : " + str(self.conversion) + " * " + str(self.baseUnit)
        else:
            return self.fullName + " (" + self.abbreviation + ") "

    def __str__(self):
        """String representation of the unit dictionary."""
        return self.abbreviation

    def isDerivedUnit(self):
        """Returns True if this unit is based on other units."""
        return (self.baseUnit != None and self.baseUnit != 0)

    def isCompoundUnit(self):
        """Returns True if this unit is a compound unit (e.g. mm/s)"""
        return self.primary_unitdict != {self:1}

    def isDimensionless(self):
        return self.baseUnit == 0

    def __call__(self, arg):
        """Returns a dFloat that is in units of self.

        If a non-dFloat is provided, these units will be applied.
        If a dFloat is provided, it will attempt to convert into these units.
        """
        return self.convert(arg)


    # ---- MATH FUNCTIONS ----
    def __mul__(self, arg):
        """Returns a new unit equivalent to this unit multiplied by the input."""
        
        new_unitdict = copy.copy(self.primary_unitdict)

        arg_unitdict, arg_value = self._getUnitDictAndValue(arg)

        unit_tuples = arg_unitdict.asUnitPowerTuples()

        for thisUnit, thisPower in unit_tuples:
            new_unitdict.add(thisUnit, thisPower)

        existing_unit = new_unitdict.isUnitary() #will return an existing unit if the dictionary only has one element to the first power, otherwise False

        if existing_unit:
            new_unit = existing_unit
        else:
            new_unit = unit(abbreviation = str(new_unitdict), fullName = "Derived Unit: " + str(new_unitdict), compound_unitdict = new_unitdict)

        if type(arg) == unit:
            return new_unit
        else:
            return dFloat(arg_value, new_unit)

    def __rmul__(self, arg):
        """Returns a new unit equivalent to the input multiplied by this unit."""
        
        new_unitdict = copy.copy(self.primary_unitdict)

        arg_unitdict, arg_value = self._getUnitDictAndValue(arg)

        unit_tuples = arg_unitdict.asUnitPowerTuples()

        for thisUnit, thisPower in unit_tuples:
            new_unitdict.add(thisUnit, thisPower)

        existing_unit = new_unitdict.isUnitary() #will return an existing unit if the dictionary only has one element to the first power, otherwise False

        if existing_unit:
            new_unit = existing_unit
        else:
            new_unit = unit(abbreviation = str(new_unitdict), fullName = "Derived Unit: " + str(new_unitdict), compound_unitdict = new_unitdict)

        if type(arg) == unit:
            return new_unit
        else:
            return dFloat(arg_value, new_unit)

    def __truediv__(self, arg):
        """Returns a new unit equivalent to this unit divided by the input."""
        
        new_unitdict = copy.copy(self.primary_unitdict)

        arg_unitdict, arg_value = self._getUnitDictAndValue(arg)

        unit_tuples = arg_unitdict.asUnitPowerTuples()

        for thisUnit, thisPower in unit_tuples:
            new_unitdict.add(thisUnit, -thisPower)

        existing_unit = new_unitdict.isUnitary() #will return an existing unit if the dictionary only has one element to the first power, otherwise False

        if existing_unit:
            new_unit = existing_unit
        else:
            new_unit = unit(abbreviation = str(new_unitdict), fullName = "Derived Unit: " + str(new_unitdict), compound_unitdict = new_unitdict)

        if type(arg) == unit:
            return new_unit
        else:
            return dFloat(1/arg_value, new_unit)

    def __rtruediv__(self, arg):
        """Returns a new unit equivalent to the input divided by this unit."""
        
        new_unitdict = copy.copy(self.primary_unitdict)
        new_unitdict.invert()

        arg_unitdict, arg_value = self._getUnitDictAndValue(arg)

        unit_tuples = arg_unitdict.asUnitPowerTuples()

        for thisUnit, thisPower in unit_tuples:
            new_unitdict.add(thisUnit, thisPower)

        existing_unit = new_unitdict.isUnitary() #will return an existing unit if the dictionary only has one element to the first power, otherwise False

        if existing_unit:
            new_unit = existing_unit
        else:
            new_unit = unit(abbreviation = str(new_unitdict), fullName = "Derived Unit: " + str(new_unitdict), compound_unitdict = new_unitdict)

        if type(arg) == unit:
            return new_unit
        else:
            return dFloat(arg_value, new_unit)

    def __pow__(self, power):
        """Returns a new unit equivalent to this unit multiplied by the input."""
        
        new_unitdict = unitdict()

        unit_tuples = self.primary_unitdict.asUnitPowerTuples()

        for thisUnit, thisPower in unit_tuples:
            new_unitdict.add(thisUnit, thisPower*power)

        existing_unit = new_unitdict.isUnitary() #will return an existing unit if the dictionary only has one element to the first power, otherwise False

        if existing_unit:
            new_unit = existing_unit
        else:
            new_unit = unit(abbreviation = str(new_unitdict), fullName = "Derived Unit: " + str(new_unitdict), compound_unitdict = new_unitdict)

        return new_unit       
    

    def _getUnitDictAndValue(self, arg):
        """Returns the unit dictionary and value for the provided argument.

        arg -- a number, dFloat, or unit

        returns unitdict, value
        """
        if type(arg) == unit:
            arg_unitdict = arg.primary_unitdict
            arg_value = None
        elif type(arg) == dFloat:
            arg_unitdict = arg.units.primary_unitdict
            arg_value = float(arg)
        else:
            arg_unitdict = unitdict()
            arg_value = float(arg)

        return arg_unitdict, arg_value


    def getBaseUnitDictionary(self):
        """Determines the base units and scaling factor of this unit.
        
        Note that this function runs recursively until a base unit has been found
        
        Returns output_unitdict, output_conversion, where:
            output_unitdict-- the base units of self
            output_conversion -- the scaling factor to go from the base units to self. derivedUnit = conversion*baseUnit
        """

        output_unitdict = unitdict()
        output_conversion = 1.0

        if self.isCompoundUnit(): #compound unit
            for thisUnit, thisPower in self.primary_unitdict.asUnitPowerTuples():
                base_unitdict, base_conversion = thisUnit.getBaseUnitDictionary()

                for baseUnit, basePower in base_unitdict.asUnitPowerTuples():
                    output_unitdict.add(baseUnit, basePower * thisPower)
                output_conversion *= (base_conversion**thisPower)

        elif self.isDerivedUnit():
            base_unitdict, base_conversion = self.baseUnit.getBaseUnitDictionary()

            for baseUnit, basePower in base_unitdict.asUnitPowerTuples():
                output_unitdict.add(baseUnit, basePower)

            output_conversion = self.conversion * base_conversion

        else:
            output_unitdict.add(self, 1.0)
            output_conversion = 1.0

        return output_unitdict, output_conversion

    def convert(self, target):
        """Converts the provided target into these units.

        target -- a unit, dFloat, or number.

        Returns dFloat, or False if units are incompatible.
        """

        this_baseunitdict, this_conversion = self.getBaseUnitDictionary()

        if type(target) == unit: #target is a unit
            that_value = 1.0
            that_unitdict, that_conversion = target.getBaseUnitDictionary()

        elif type(target) == dFloat: #target is a dFloat
            that_value = float(target)
            that_unitdict, that_conversion = target.units.getBaseUnitDictionary()

        else: #target is presumably a number.
            return dFloat(target, self)

        equivalency = this_baseunitdict.isEquivalent(that_unitdict)

        if equivalency == 0:
            return False

        else:
            #derived_units = conversion * base_units
            that_value_baseunits = that_value / that_conversion
            that_value_thisunits = that_value_baseunits * (this_conversion**equivalency)

            return dFloat(that_value_thisunits, self)




class unitdict(dict):
    """A dictionary subclass used to store units and their powers.

    This is the core of the unit system. Units are stored in the form {unit: power, ...}
    """

    def __init__(self, inputDictionary = {}):
        """Initialization function for unit dictionary.
        
        inputDictionary -- a seed dictionary in the form {unitObject:unitPower,...}
        """       
        dict.__init__(self, inputDictionary)

    
    def add(self, newUnit, power):
        """Adds a unit to the unitdict.

        newUnit -- a unit object to be added
        power -- the power to which this unit object is to be added.
        """

        if newUnit in self: #The unit is already in the dictionary
            newPower = self[newUnit] + power
            if newPower == 0:
                self.pop(newUnit)
            else:
                self.update({newUnit:newPower})

        else: #unit is not in the dictionary yet
            self.update({newUnit: power})

    def invert(self):
        """Inverts the unit dictionary."""
        for unit in self:
            power = self[unit]
            self.update({unit: -power})

    def isUnitary(self):
        """If the dictionary consists of only one unit raised to the 1st power, this unit is returned, otherwise False."""
        if len(self) == 1:
            for key in self:
                if self[key] == 1:
                    return key
                else:
                    return False
        else:
            return False

    def isEmpty(self):
        """Returns True if this unit dictionary is empty."""
        return dict.__eq__(self, {})

    def asUnitPowerTuples(self):
        """Returns the unitdict as a list of (unit, power) tuples."""
        return [(thisUnit, self[thisUnit]) for thisUnit in self]

    def removeDimensionlessUnits(self):
        """Removes all dimensionless units from the dictionary."""
        for thisUnit in dict(self):
            if thisUnit.isDimensionless():
                self.pop(thisUnit)


    def __eq__(self, other):
        """Compares this unit dictionary against another.

        We are overriding this class because we need to filter out any dimensionless units before doing the comparison.
        """
        this_unitdict = copy.copy(self)
        this_unitdict.removeDimensionlessUnits()

        that_unitdict = copy.copy(other)
        that_unitdict.removeDimensionlessUnits()

        return dict.__eq__(this_unitdict, that_unitdict)
    

    def isEquivalent(self, other):
        """Returns the equivalency of this unitdict to another unitdict.
        
        Equivalency is defined as numbers whose BASE units are either equal or reciprocals.
        
        Returns the power of the equivalency (1 or -1), or 0 if the units are not equivalent
        """  
        this_unitdict = copy.copy(self)
        this_unitdict.removeDimensionlessUnits()

        that_unitdict = copy.copy(other)
        that_unitdict.removeDimensionlessUnits()

        if dict.__eq__(this_unitdict, that_unitdict): #they are equal
            return 1

        that_unitdict.invert()

        if dict.__eq__(this_unitdict, that_unitdict): #they are inverses of each other
            return -1

        return 0 #not equal


    def __str__(self):
        """String representation of the unit dictionary."""
        numeratorUnits = [(numeratorUnit, self[numeratorUnit]) for numeratorUnit in self if self[numeratorUnit] > 0]
        denominatorUnits = [(denominatorUnit, self[denominatorUnit]) for denominatorUnit in self if self[denominatorUnit] < 0]
         
        returnString = '' #this is the seed of the return string that will be built upon

        #fill in numerator string if no units are in the numerator
        if numeratorUnits == [] and denominatorUnits != []:
            returnString += "1"
         
        #fill in numerator string
        for numeratorUnit, numeratorValue in numeratorUnits: #iterate over all units in numerator
            if numeratorValue > 1: #more than to the first power
                returnString += numeratorUnit.abbreviation + '^' + str(int(numeratorValue)) + '*'
            else:
                returnString += numeratorUnit.abbreviation + '*'


        if numeratorUnits != []: returnString = returnString[:-1] #remove trailing *
         
        if denominatorUnits != []: returnString += '/' #add trailing /
         
        for denominatorUnit, denominatorValue in denominatorUnits: #iterate over all units in denominator
            if denominatorValue < -1: #more than to the first power
                returnString += denominatorUnit.abbreviation + '^' + str(-int(denominatorValue)) + '*'
            else:
                returnString += denominatorUnit.abbreviation + '*'
         
        if denominatorUnits != []: returnString = returnString[:-1] #remove trailing *
         
        return returnString


class dFloat(float):
    """A dimensional floating-point number, i.e. a float with units."""
    
    def __new__(self, value, units = None):
        """Constructor for dFloat that overrides float.__new__
        
        value -- the value of the floating point number.
        units -- a unit object
        """
        return float.__new__(self, value)
    
    def __init__(self, value, units = None):
        """Initializes the dFloat.
        
        units -- a unit object
        """
        
        if units == None:
            raise errors.UnitError("dFloat must be initialized with units.")
        else:
            self.units = units
    
    def __str__(self):
        """String representation of the dFloat number"""
        
        return str(float(self)) + ' ' + str(self.units)
    

    #--- OVERRIDE MATH FUNCTIONS ---
    def __add__(self, other):
        """Overrides addition.
        
        other -- the right-hand number to add
        """
        if type(other) != dFloat:
            raise errors.UnitError("cannot add dFloats to non-dFloats")

        if self.units.primary_unitdict != other.units.primary_unitdict: #REPLACE with conversion convenience, when ready.
            other_converted = self.units(other)
            if other_converted is False:
                raise errors.UnitError("addition operand units don't match " + str(self.units) + " vs " + str(other.units))
            else:
                other = other_converted

        value = float(self) + float(other) #perform numerical addition

        return dFloat(value, self.units)
    
    def __sub__(self, other):
        """Overrides subtraction.
        
        other -- the right-hand number to subract.
        """

        if type(other) != dFloat:
            raise errors.UnitError("cannot subtract dFloats to non-dFloats")

        if self.units.primary_unitdict != other.units.primary_unitdict: #REPLACE with conversion convenience, when ready.
            other_converted = self.units(other)
            if other_converted is False:
                raise errors.UnitError("subtraction operand units don't match: " + str(self.units) + " vs " + str(other.units))
            else:
                other = other_converted
        value = float(self) - float(other) #perform numerical subtraction

        return dFloat(value, self.units)
    
    def __neg__(self):
        """Overrides negation."""
        value = -float(self)
        units = unitDictionary(self.units)
        return dFloat(value, units)
    
    def __abs__(self):
        """Overrides absolute value."""
        return dFloat(abs(float(self)), self.units)
        
        
    def __mul__(self, other):
        """Overrides left-hand multiplication."""
        if type(other) == unit:
            return dFloat(float(self), self.units * other)

        elif type(other) == dFloat:
            return dFloat(float(self)*float(other), self.units * other.units)

        else:
            return dFloat(float(self)*float(other), self.units)


    
    def __rmul__(self, other):
        """Overrides right-hand multiplication.
        
        other -- left-hand number to be multiplied.
        
        Note that this will only be called if the left-hand number is not a dFloat or unit.
        """
        return dFloat(float(self)*float(other), self.units)
    

    def __truediv__(self, other):
        """Overrides left-hand division."""

        if type(other) == unit:
            return dFloat(float(self), self.units / other)

        elif type(other) == dFloat:
            return dFloat(float(self)/float(other), self.units / other.units)

        else:
            return dFloat(float(self)/float(other), self.units)
    

    def __rtruediv__(self, other):
        """Overrides right-hand division.
        
        other -- the left-hand number to divide.
        
        Note that this will only be called if the left-hand number is not a dFloat.
        """

        return dFloat(float(other)/float(self), 1/self.units)
    

    def __pow__(self, power):
        """Overrides exponential.
        
        power -- the power to raise this value to.
        """
        value = float(self)**float(power)
        newUnits = self.units ** power
        return dFloat(value, newUnits)

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
N = unit('N', 'newton', kg*m/s**2, 1) #newtons are the base unit of force. Eventually need to build in a derived unit system to convert into SI base units.
kgf = unit('kgf', 'kilogram force', N, 1.0/9.80665)
gf = unit('gf', 'gram force', kgf, 1000.0)
ozf = unit('ozf', 'ounce force', gf, 0.035274)
lbf = unit('lbf', 'pound force', ozf, 1.0/16.0)

# power - mechanical
W = unit('W', 'watt', N*m/s, 1.0)

# electrical
V = unit('V', 'volt')
A = unit('A', 'amp')


# pseudo-units
# these units are just to make it easier to keep track of transformations thru the system, and are not necessarily SI units
step = unit('step', 'step') #steps are base units
px = unit('px', 'pixels') #pixels are base units
n = unit('n', 'number', 0) #non-dimensional units