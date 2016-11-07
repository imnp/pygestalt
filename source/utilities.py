#   pyGestalt Utilities Module

"""Provides a host of common utility functions used across the pyGestalt framework."""


#---- IMPORTS ----
import math
import ast
import datetime
import itertools
import sys
from pygestalt import config

def callFunctionAcrossMRO(instance, functionName, args = (), kwargs = {}, parentToChild = True):
    """Calls a function on all classes in instance's method resolution order.
    
    instance -- the instance to be provided to the class methods, and also used to pull the method resolution order list.
    functionName -- the name of the function to be called
    args -- positional arguments to be passed to the function
    kwargs -- keyward arguments to be passed to the function
    parentToChild -- affects the order in which base classes are called. If true, will walk up derived classes from basest base class.
    
    This function is particularly useful in initialiation routines where the same function must be called across multiple derived classes.
    
    Note that this only currently works with functions that do not return anything.
    """
    
    mro = instance.__class__.mro()  #grab the MRO from the instance
    if parentToChild:
        mro.reverse()   #need to reverse MRO so iterates up derived class chain
        
    for thisClass in mro:   #iterate over classes in method resolution order
        if functionName in thisClass.__dict__:  #check to make sure class has function defined in __dict__. This prevents calling a base class's method multiple times.
            thisClass.__dict__[functionName](instance, *args, **kwargs)   #call class function on instance with provided arguments

def objectIdentifier(callingObject):
    """Returns a human-readable string identifier for a provided object.
    
    callingObject -- the object to be identified
    
    This method figures out the best name to use in identifying an object, taking queues from:
    - its _name_ attribute, if avaliable
    - more to be added as this evolves...
    
    Returns a string that can be used to identify the object to the user.
    """
    if hasattr(callingObject, '_name_'):    #object has a _name_ attribute
        name = getattr(callingObject, '_name_')
        if name:    #name is not False (or None)
            return name #just return the name
        else:   #name is False or None
            return callingObject.__class__.__name__ + " @ " + hex(id(callingObject)) #_name_ is None or False, return a reinterpretation of the str representation
    else:
        return callingObject.__class__.__name__ + " @ " + hex(id(callingObject)) #no _name_ attribute, return a reinterpretation of the object str representation   
    
    
def notice(callingObject, noticeString):
    """Prints a formatted notice in the terminal window that includes the name of the source.
    
    callingObject -- the instance object making the call
    noticeString -- the message to be printed
    
    For now this function just prints to the terminal, but eventually it could publish to a browser-based interface etc...
    """
    print "[" + objectIdentifier(callingObject) + "] " + str(noticeString) #print objectRepr: message

def printToTerminal(text, newLine = True):
    """Prints text to the terminal window, with or without a carriage return."""
    if newLine == True: #print with carriage return
        print text
    else: #print without carriage return
        sys.stdout.write(text)
        sys.stdout.flush()

def debugNotice(callingObject, channel, noticeString, padding = False, newLine = True):
    """If global verbose debug is enabled, this function will print a formatted notice in the terminal window or alternate target.
    
    callingObject -- the instance object making the call
    channel -- a string channel name, which allows filtering debug output if desired (not currently enabled)
    noticeString -- the message to be printed
    padding -- if true, inserts a carraige return to pad the top of the notice
    newLine -- if false, will output without a newline character
    
    Currently assigned channels:
        _gestaltInterfaceTransmit_ -- messages from the gestalt interface transmit function
        _gestaltNodeInboundRouter_ -- messages from the base gestalt node inbound packet router
    
    Returns True if notice was printed (verbose debug is enabled), or False otherwise
    """
    if config.verboseDebug() and config.debugChannelEnabled(channel):
        if padding: print ""
        if callingObject == None:
            printToTerminal(str(noticeString), newLine)
        else:
            printToTerminal("[" + objectIdentifier(callingObject) + "] " + str(noticeString), newLine)
        return True
    else:
        return False

def unsignedIntegerToBytes(integer, numbytes):
    """Converts an unsigned integer into a sequence of bytes, LSB first.
    
    integer -- the number to be converted
    numbytes -- the number of bytes to be used in representing the integer
    """
    bytes = range(numbytes)
    for i in bytes:
        bytes[i] = int(integer%256)
        integer -= integer%256
        integer = int(integer//256)
        
    if integer>0: raise IndexError('Overflow in conversion between uint and byte list.')
    else: return bytes
    
def bytesToUnsignedInteger(byteList):
    """Converts a little-endian sequence of bytes into an unsigned integer."""
    value = 0   #initialize at 0
    for order, byte in enumerate(byteList):
        value += byte*(256**order)
    return value


def signedIntegerToTwosComplement(integer, bitSize):
    """Converts a signed integer into an unsigned two's complement representation.
    
    integer -- the number to be converted.
    bitSize -- the length in bits of the two's complement number to be returned.
    """
    maxSize = (2**bitSize)/2 - 1
    if abs(integer) > maxSize: #integer cannot be expressed in size
        raise ValueError("Cannot convert signed integer to twos complement. Input value of " + str(integer) + " exceeds maximum size (+/- " + str(maxSize)+").") 
    if integer >= 0: return int(integer) #integer is positive, so nothing needs to be done.
    else:
        allOnes = 2**bitSize - 1 # fills bitSize bits with all ones
        return (allOnes^abs(int(integer))) + 1  #inverts just the bits comprising the original number, and adds one. This is two's complement!

def twosComplementToSignedInteger(twosComplement, bitSize):
    """Converts a twos-complement representation into a signed integer.
     
    twos-complement -- the number to be converted.
    bitSize -- the length in bits of the two's complement input.
    """
           
    signBitPosition = bitSize - 1    #sign bit is the most significant bit
    signBit = 2**signBitPosition    #a single bit in the MSB position
    if(signBit & twosComplement):   #number is negative, need to take two's complement
        allOnes = 2**bitSize - 1 # fills size bytes with all ones
        return -((twosComplement - 1)^allOnes)   #subtract one then flip bits, the is the inverse of encoding process.
    else:
        return twosComplement #positive number, no need to do anything.
 
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

def changeBitInInteger(integer, bitPosition, bitValue):
    """Modifies a provided integer by either setting or clearing a specified bit.
    
    integer -- the number in which to modify a bit
    bitPosition -- the position of the bit in the integer, starting with the LSB = 0
    bitValue -- the value to which the bit should be changed, either True or False
    
    returns the modified integer.
    """
    shiftedBitValue = 1<<bitPosition
    if bitValue:
        return (integer | shiftedBitValue)
    else:
        return (integer & ~shiftedBitValue)

def fuzzyEquals(number1, number2, tolerance):
    """Returns True if both provided numbers are within a specified distance.
    
    number1, number2 -- the two numbers to be compared
    tolerance -- the maximum distance between both numbers in order to consider them equal.
    """
    delta = abs(number1-number2)
    if abs(delta)< tolerance:
        return True
    else: return False
    
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

class intelHexParser(object):
    """Parses Intel Hex Files for Bootloading and Memory Programming."""
    def __init__(self):
        """Initializes the Intel Hex Parser."""
        self.filename = None
        self.hexFile = None
        self.resetParser()
    
    def openHexFile(self, filename = None):
        """Opens an Intel Hex file for parsing.
        
        filename -- the string filename of the hex file to be opened.
        """
        if filename != None:
            self.hexFile = open(filename, 'r')
            return self.hexFile
        else:
            print "intelHexParser: please provide a filename!"
            return False
        
    def resetParser(self):
        """Resets the state of the parser."""
        self.baseByteLocation = 0    #always initialize at location 0, this can be changed by the hex file during reading
        self.parsedFile = []
        self.codeStart = 0
        self.terminated = False    #gets set when end of file record is reached
    
    def loadHexFile(self):
        """Parses and loads an opened hex file into internal memory."""
        parseVectors = {0:self.processDataRecord, 1: self.processEndOfFileRecord, 2: self.processExtendedSegmentAddressRecord,
                    3:self.processStartSegmentAddressRecord, 4: self.processExtendedLinearAddressRecord, 5: self.processStartLinearAddressRecord}

        for index, record in enumerate(self.hexFile):    #enumerate over lines in hex file
            integerRecord = self.integerRecord(self.recordParser(record))
            parseVectors[integerRecord['RECTYP']](integerRecord)
#        print self.parsedFile
        self.checkAddressContinuity()
        
    def returnPages(self, pageSize):
        """Segments a loaded hex file into pages of a specified size.
        
        pageSize -- the size in bytes of each page
        
        Returns a list containing byte lists, each representing a page of size pageSize
        """
        numPages = int(math.ceil(len(self.parsedFile)/float(pageSize)))    #number of pages
        pages = [self.parsedFile[i*pageSize:(i+1)*pageSize] for i in range(numPages)]    #slice parsed data into pages of size pageSize
        
        #fill in last page
        lastPage = pages[-1]
        delta = pageSize - len(lastPage)
        lastAddress = lastPage[-1][0]    #address of last entry in last page
        makeUp = [[lastAddress+i+1, 0] for i in range(delta)]
        pages[-1] += makeUp    #fill last page
        
        return pages
        
    def recordParser(self, record):
        record = record.rstrip()
        length = len(record)
        return {'RECLEN':record[1:3], 'OFFSET':record[3:7], 'RECTYP':record[7:9], 'DATA':record[9:length-2], 'CHECKSUM':record[length-2: length]}
            
            
    def integerRecord(self, record):
        return {'RECLEN':int(record['RECLEN'],16), 'OFFSET':int(record['OFFSET'], 16), 'RECTYP':int(record['RECTYP'],16),
             'CHECKSUM': int(record['CHECKSUM'], 16), 'DATA': self.dataList(record['DATA'])}
        
        
    def dataList(self, data):
        return [int(data[i:i+2], 16) for i in range(0, len(data), 2)]
    
    
    def processDataRecord(self, record):
        codeLocation = record['OFFSET'] + self.baseByteLocation
        for index, byte in enumerate(record['DATA']):
            self.parsedFile +=[[codeLocation + index, byte]]
    
    def processEndOfFileRecord(self, record):
        self.terminated = True
    
    def processExtendedSegmentAddressRecord(self, record):
        self.baseByteLocation = (record['DATA'][0]*256 + record['DATA'][1])*16    #value is shifted by four bits
    
    def processStartSegmentAddressRecord(self, record):
        print "Start Segment Address Record Encountered and Ignored"
    
    def processExtendedLinearAddressRecord(self, record):
        print "Extended Linear Address Record Encountered and Ignored"
    
    def processStartLinearAddressRecord(self, record):
        print "Start Linear Address Record Encountered and Ignored"
        
    def checkAddressContinuity(self):
        baseAddress = self.parsedFile[0][0]    #inital address entry
        for byte in self.parsedFile[1::]:
            if byte[0] == baseAddress + 1:
                baseAddress += 1
                continue
            else:
                print "CONTINUITY CHECK FAILED"
                return False
        
        print "CONTINUITY CHECK PASSED"
        