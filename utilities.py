#   pyGestalt Utilities Module

"""Provides a host of common utility functions used across the pyGestalt framework."""


#---- IMPORTS ----
import math
import ast
import datetime
import itertools

def unsignedIntegerToBytes(integer, numbytes):
    """Converts an unsigned integer into a sequence of bytes, LSB first."""
    bytes = range(numbytes)
    for i in bytes:
        bytes[i] = int(integer%256)
        integer -= integer%256
        integer = int(integer//256)
        
    if integer>0: raise IndexError('Overflow in conversion between uint and byte list.')
    else: return bytes
    
def signedIntegerToTwosComplement(integer, size):
    """Converts a signed integer into an unsigned two's complement representation.
    
    integer -- the number to be converted.
    size -- the length in bytes of the two's complement number to be returned.
    """
    if integer >= 0: return integer #integer is positive, so nothing needs to be done.
    else:
        allOnes = 256**size - 1 # fills size bytes with all ones
        return (allOnes^abs(integer)) + 1  #inverts just the bits comprising the original number, and adds one. This is two's complement!
    
 
def flattenList(inputList):
    """Flattens shallow nested lists into a single list.
    
    Note that this will only work for nesting that is one level deep.
    """
    outputList = []
    for item in inputList:
        if hasattr(item, '__iter__'): outputList += item
        else: outputList += [item]  #catches case that item is not a list, and doesn't need to be flattened.
    return outputList

def listToString(inputList):
    """Converts a list of integers into an ASCII string."""
    return ''.join([chr(i) for i in inputList])

def stringToList(inputString):
    """Convert a string into a list of integers."""
    return [ord(i) for i in inputString]

class CRC():
    """Generates and validates CRC values."""
    def __init__(self, polynomial = 7):
        """Initializer for a CRC instance.
        
        polynomial -- the taps used to generate the CRC. Default is 7 (ATM), could also use 49 (Dallas-Maxim)
        """
        self.polynomial = polynomial        #CRC-8: ATM=7, Dallas-Maxim = 49
        self.crcTable = self.crcTableGen()
    
    def calculateByteCRC(self, byteValue):
        """Calculates Bytes in the CRC Table."""
        for i in range(8):
            byteValue = byteValue << 1
            if (byteValue//256) == 1:
                byteValue = byteValue - 256
                byteValue = byteValue ^ self.polynomial
        return byteValue
    
    def crcTableGen(self):
        """Generates and returns a CRC table to make CRC generation faster."""
        crcTable = []
        for i in range(256):
            crcTable += [self.calculateByteCRC(i)]
        return crcTable
    
    def generate(self, byteList):
        """Generates a CRC byte from an input list of bytes.
        
        byteList -- a flat list containing a sequence of bytes for which to generate a CRC.
        """
        #INITIALIZE CRC ALGORITHM
        crc = 0
        crcByte = 0
        
        #CALCULATE CRC
        for byte in byteList:
            crcByte = byte^crc
            crc = self.crcTable[crcByte]
        return crc
    
    def validate(self, byteList, checkCRC):
        """Checks CRC byte against list CRC.
        
        byteList -- a flat list containing a sequence of bytes against which to check the CRC.
        checkCRC -- the CRC value to check against.
        """
        
        actualCRC = self.generate(byteList) #calculate CRC of list
        
        if actualCRC != checkCRC:    return False    #CRC doesn't match
        else:    return True    #CRC matches