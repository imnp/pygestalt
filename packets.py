#   pyGestalt Packets Module

"""Provides a fremework for templating, encoding, and decoding packets."""

#--IMPORTS--
from pygestalt import utilities

class template(object):
    """Stores the formatting used to encode and decode serialized data packets."""
    def __init__(self, *packetTokens):
        """Initialize a new template.
        
        packetTokens -- an ordered list of elements that comprise a packet. If the first argument is a string, it will be treated as the packet name.
        """
        
        if type(packetTokens[0]) == str:    # the first argument is a string. We'll assume that's the name of the template.
            self.name = packetTokens[0] # give this template a name!
            self.template = packetTokens[1:] # the internally stored template is just the list of arguments in the order they were provided, minus the name.
        else: 
            self.name = None  # a nameless template :-(
            self.template = packetTokens    # the internally stored template is just the list of arguments in the order they were provided. 
              
    def __call__(self, input):
        """A shortcut to either encode or decode a packet.
        
        Calling the template instance directly will have the effect of either
        encoding or decoding a packet, depending on the type provided as input.
        
        input -- if a dict, will return an encoded packet. If a list or packet, will return a decoded dictionary.
        """
        if type(input) == dict: # Provided input is a dictionary, so user wants to encode dictionary as packet.
            return self.encode(input)
        if type(input) == list or type(input) == packet:    # Provided input is a list or packet, so user wants to decode into a dictionary
            return self.decode(input)
    
    def encode(self):
        '''Serializes a packet using the token list stored in self.template.'''
        pass
        
    
    def decode(self):
        pass
    
class packet(list):
    """The type used for storing serialized packets.
    
    This type should act like a list while retaining a link to the template used to encode the packet.
    """
    def __init__(self, value = [], template = None):
        """Initialize a new packet.
        
        value -- an input list, or packet. Note that any meta-data such as template of an input packet will be lost.
        template -- the template used to generate this packet. Useful for updating etc...
        """
        list.__init__(self, value)
        self.template = template

class packetToken(object):
    """Base class for creating packet tokens, which are elements that handle encoding and decoding each segment of a packet."""
    
    def __init__(self, keyName, *args):
        """Initialize a new packet token.
        
        keyName -- a reference name for the token that will match a key in an encoding dictionary, or be provided as a key during decoding.
        """
        self.keyName = keyName  # permanently store keyName
        self.init(*args)    # call subclass init function to do something with additional arguments.
    
    def init(self, *args):
        """Secondary initializer should be over-ridden by subclass.""" 
        pass
    
    def encode(self, encodeDict, templateName = None):
        """Serializes the value keyName in encodeDict using the subclass's _encode_ method.
        
        encodeDict -- a dictionary of values to be encoded. Only the value who's key matches keyName will be encoded by the method.
        templateName -- the name of the calling template, used for debugging.
        """
        if self.keyName in encodeDict:  # keyName has a matching value in the encodeDict, proceed!
            return self._encode_(encodeDict[self.keyName]) # call the subclass's _encode_ method for token-specific processing.
        else: # no keyName has been found, so compose a useful error message and raise an exception.
            if templateName: errorMessage = str(self.keyName) + " not found in template " + templateName + "."
            else: errorMessage = str(self.keyName) + " not found in template."
            raise KeyError(errorMessage)


class unsignedInt(packetToken):
    """An unsigned integer token type."""
    
    def init(self, length = 1):
        """Initializes the unsigned integer token.
        
        length -- the length in bytes of the unsigned integer.
        """
        self.length = length # length of unsigned integer
    
    def _encode_(self, encodeValue):
        """Converts an unsigned integer into a sequence of bytes."""
        return utilities.unsignedIntegerToBytes(encodeValue, self.length)