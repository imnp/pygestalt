#   pyGestalt Packets Module

"""Provides a fremework for templating, encoding, and decoding packets."""

#--IMPORTS--
from pygestalt import utilities
import itertools
import math
import errors

class serializedPacket(list):
    """The type used for storing serialized packets.
    
    This type should act like a list while retaining a link to the template used to encode the packet.
    """
    def __init__(self, value = [], template = None):
        """Initialize a new packet.
        
        value -- an input list, or packet. Note that any meta-data such as template of an input packet will be lost.
        template -- the template used to generate this packet. Useful for updating etc...
        """
        list.__init__(self, utilities.flattenList(value))
        self.template = template
    
    def toString(self):
        """A shortcut to get the serialized packet in the format of a string."""
        return utilities.listToString(self)
    
    def toList(self):
        """A shortcut to get the serialized packet in the form of a stripped list."""
        return list(self)
        

class emptyTemplate(object):
    """A template that encodes and decodes no tokens.
    
    The reason for a breaking this out into a seperate class is that the standard template class MUST contain tokens
    because of how the length verification works.
    """
    def __init__(self, name = ""):
        """Initialize the empty template."""
        self.name = name
        self.template = []
    
    def __call__(self, input):
        """A shortcut to either encode or decode a packet.
        
        Calling the template instance directly will have the effect of either
        encoding or decoding a packet, depending on the type provided as input.
        
        input -- if a dict, will return an EMPTY packet. If a list or packet, will return a EMPTY dictionary.
        """
        if type(input) == dict: # Provided input is a dictionary, so user wants to encode dictionary as packet.
            return self.encode(input)
        if type(input) == list or type(input) == packet:    # Provided input is a list or packet, so user wants to decode into a dictionary
            return self.decode(input)
        
    def encode(self, input):
        """Returns an empty packet."""
        return serializedPacket([], self)
    
    def decode(self, input):
        """Returns an empty dictionary following the same format as template.decode"""
        return {}, []   #empty dictionary, empty working packet

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
            self.name = ""  # a nameless template :-(
            self.template = packetTokens    # the internally stored template is just the list of arguments in the order they were provided. 

        self.template = list(self.template) #convert from tuple to list
        for token in self.template: token.parentTemplateName = self.name    # gives each token a reference to this template's name for error output.
        self.size = self.calculateTemplateSize(self.template)
        self.validateTemplate()
    
    def validateTemplate(self):
        """Validates that template is properly composed."""
        
        errorFlag = False   #used to keep track of whether an error occured
        
        #run a series of tests
        if self.size < 0:   # template has too many unbounded tokens
            errorMessage = "Cannot compose template " + self.name +". More than one tokens have unbounded lengths!"
            errorFlag = True
        
        if errorFlag:
            raise errors.CompositionError(errorMessage)
    
    def validateChecksum(self, checksumName, inputPacket):
        """Compares the packet's checksum with the calculated checksum and returns true if equal.
        
        checksumName -- the text name of the checksum token in the packet template.
        inputPacket -- the packet to be validated.
        
        The checksum data is extracted from the packet, and the checksum token is used to calculate
        the checksum of the remainder of the packet. Then the provided and calculated checksums are compared.
        """
        tokenStartIndex, tokenEndIndex, checksumToken = self.findTokenPosition(checksumName, inputPacket)   #locate checksum position in packet
        providedChecksum = inputPacket[tokenStartIndex:tokenEndIndex][0] #isolate checksome value from packet. Comes in as list so pull integer.
        remainingPacket = inputPacket[:tokenStartIndex] + inputPacket[tokenEndIndex:] #strip out checksum value from packet
        calculatedChecksum = checksumToken.encode(encodeDict = {}, inProcessPacket = remainingPacket) #calculate checksum of remaining packet
        return calculatedChecksum == providedChecksum #return comparison of checksums
            
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
    
    @staticmethod
    def calculateTemplateSize(template):
        """Determines the size of a provided template.
        
        Size will be returned as either > 0 for a determinate sized packet, 0 for packets of unbounded size, and -1 for
        packets with more than one tokens that have unbounded sizes. This condition should fail the validation function.
        Note that the word size is used instead of length to distinguish from the length token, which can report size
        either self-inclusive or not, and does not include any checksums.
        
        template -- the template whose size should be calculated.
        
        return value:
            >0 -- size of template in  bytes
            0 -- template has unbounded size
            -1 -- template is invalid, has more than one tokens of unbounded size 
        """
        size = -1   #first pass value
        for token in template:  # iterate thru all tokens in the template
            if size == -1: # first pass
                size = token.size
            elif size == 0: # template size is unbounded
                if token.size == 0: # template contains at least two tokens of unbounded size.
                    size = -1 # mark template as invalid
                    break   # no need to continue
            else:   #so far, template has a determinate size
                if token.size == 0: #token has an unbounded size
                    size = 0    #template now  has an unbounded size
                else:
                    size += token.size
        return size
                
                
    def encode(self, encodeDict, *args, **kwargs):
        """Serializes a packet using the token list stored in self.template.
        
        encodeDict -- the input dictionary that needs to get encoded using the template.
        *args and **kwargs -- here to catch un-needed terms because this encode function needs to be interchangeable with a packet
                              token to permit embedding packets.
                              
        Returns a packets.serializedPacket object.
        """
        
        #1) Encode tokens that don't require information on the in-process packet, i.e. NOT length and checksum tokens 
        inProcessPacket = [token.encode(encodeDict) for token in self.template]
        
        #2) Encode length tokens, all others get copied without calling an encode method. At this point most tokens will be lists.
        inProcessPacket = [token.encode(encodeDict, inProcessPacket) if type(token) == length else token for token in inProcessPacket]
        
        #3) Encode checksum tokens, all others get copied without calling an encode method.
        inProcessPacket = [token.encode(encodeDict, inProcessPacket) if type(token) == checksum else token for token in inProcessPacket]
                    
        return serializedPacket(inProcessPacket, self)  #convert into packet type, giving a reference to the template, and return
    
    
    def decode(self, inputPacket, forwardDecode = True):
        """Deserializes a packet, using the token list stored in self.template, into a key:value dictionary.
        
        inputPacket -- either a list or packets.packet that contains a serial stream of data to be decoded by the template.
        forwardDecode -- if true, primary decode direction is forwards (left to right). If false, primary decode direction is reverse.
        
        The decoding algorithm works by feeding the packet thru a chain of tokens, each of which will strip their component
        of the packet. It becomes complicated by tokens without a fixed length. This is handled by working in one direction until
        an unbounded token is encountered (the primary pass), then changing direction thru the remainder of the packets.
        
        Returns (decodeDict, workingPacket) where:
        decodeDict -- the set of key:value pairs decoded by the template
        workingPacket -- whatever packet remains after decoding. If template is not embedded in another template, this should be []
        """
        workingPacket = list(inputPacket) # converts packets.packet to a list, and establishes a working copy.
        if forwardDecode:   #template direction depends on decode direction
            workingTemplate = self.template
        else:
            workingTemplate = [token for token in reversed(self.template)]  #generate a reverse template 
        decodeDict = {}   # stores the growing dictionary of decoded packet values.
        
        # PRIMARY PASS -- iterate over template in primary direction
        for tokenIndex, token in enumerate(workingTemplate):
            if token.size > 0:  #token has a fixed size, continue in primary pass
                decodedKeyValuePairs, workingPacket = token.decode(workingPacket, forwardDecode)
                decodeDict.update(decodedKeyValuePairs)    #updated decodeDict with key:value pairs decoded by token
                continue
            else:
                tokenIndex -= 1 #roll back the token index so that it's included in the secondary pass 
                break
        
        # SECONDARY PASS -- iterate over remaining template in reverse direction
        forwardDecode = not(forwardDecode)  #reverse the direction of decoding
        for token in reversed(workingTemplate[tokenIndex+1:]):    #tokenForwardIndex + 1 is the next token in the template. If no secondary pass, this will iterate over an empty list
            decodedKeyValuePairs, workingPacket = token.decode(workingPacket, forwardDecode)
            decodeDict.update(decodedKeyValuePairs)  #update decodeDict with key:value pairs decoded by token
        
        return decodeDict, workingPacket
    
    def findTokenPosition(self, tokenName, inputPacket, forwardDecode = True):
        """Returns the index range that a referenced token spans in the input packet.
        
        tokenName -- the string name of the token to be found
        inputPacket -- the input packet to be analyzed by the template while searching for the token.
        
        Uses the same decoding algorithm as the decode function, but rather than passing the packet to each token
        for digestion, each token's size attribute is used to advance (or decrement if a reverse pass) the index position.
        This function is typically used internally to do things like validate a checksum.
        
        Returns (indexRange, token) where:
        startIndex -- the beginning index of the sub-list matching the token
        endIndex -- the ending index of the sub-list matching the token
        token -- the token object whose name is provided by the tokenName input argument.
        """
        
        workingPacket = list(inputPacket) # converts packets.packet type to a list, and establishes a working copy.
        packetLength = len(workingPacket) # length of packet
        if forwardDecode:   #template direction depends on on decode direction
            workingTemplate = self.template
            searchIndexPosition = 0 #keeps track of the starting index of the token currently being examined, from the start of the packet
        else:
            workingTemplate = [token for token in reversed(self.template)]
            searchIndexPosition = packetLength  #working from end of packet, so index starts there
        
        #PRIMARY PASS -- iterate over template in primary direction
        for tokenIndex, token in enumerate(workingTemplate):
            if token.size > 0:  #token has finite size, continue with primary pass
                if forwardDecode:   #calculate token span indices
                    tokenStartIndex = searchIndexPosition #going forward, so token starts at the search index position
                    tokenEndIndex = searchIndexPosition + token.size #offset forwards by the token size
                else:
                    tokenStartIndex = searchIndexPosition - token.size #going in reverse, so token starts at the search index position offset in reverse by the token length
                    tokenEndIndex = searchIndexPosition
                
                if type(token) == template or type(token) == packetTemplate: #the token is another template, forward on the search to it.
                    searchStartIndex, searchEndIndex, searchToken = token.findTokenPosition(tokenName, workingPacket[tokenStartIndex:tokenEndIndex], forwardDecode)
                    tokenEndIndex = tokenStartIndex + searchEndIndex
                    tokenStartIndex += searchStartIndex
                    if searchToken != None: #Token found in embedded template!
                        return tokenStartIndex, tokenEndIndex, searchToken
                else:   #not an embedded template
                    if token.keyName == tokenName: #Found! This happens after checking for templates because those have names but should be recursively searched, not returned.
                        return tokenStartIndex, tokenEndIndex, token
                
                #token not found, update search index position and continue
                if forwardDecode: searchIndexPosition = tokenEndIndex
                else: searchIndexPosition = tokenStartIndex
                continue
            else:  #token has unbounded size, begin secondary pass
                tokenIndex -= 1 #roll back tokenIndex so that it is included in secondary pass
                break #go on to secondary pass
        
        # SECONDARY PASS -- iterate over remaining template in reverse direction
        forwardDecode = not(forwardDecode)  #reverse the direction of decoding
        primaryPassSearchIndexPosition = searchIndexPosition
        if forwardDecode:
            searchIndexPosition = 0
        else:
            searchIndexPosition = packetLength
            
        for token in reversed(workingTemplate[tokenIndex+1:]):    #tokenForwardIndex + 1 is the next token in the template. If no secondary pass, this will iterate over an empty list
            if token.size > 0:  #token has finite size, continue with primary pass
                if forwardDecode:   #calculate token span indices
                    tokenStartIndex = searchIndexPosition #going forward, so token starts at the search index position
                    tokenEndIndex = searchIndexPosition + token.size #offset forwards by the token size
                else:
                    tokenStartIndex = searchIndexPosition - token.size #going in reverse, so token starts at the search index position offset in reverse by the token length
                    tokenEndIndex = searchIndexPosition
                
                if type(token) == template or type(token) == packetTemplate: #the token is another template, forward on the search to it.
                    searchStartIndex, searchEndIndex, searchToken = token.findTokenPosition(tokenName, workingPacket[tokenStartIndex:tokenEndIndex], forwardDecode)
                    tokenEndIndex = tokenStartIndex + searchEndIndex
                    tokenStartIndex += searchStartIndex
                    if searchToken != None: #Token found in embedded template!
                        return tokenStartIndex, tokenEndIndex, searchToken
                else:   #not an embedded template
                    if token.keyName == tokenName: #Found! This happens after checking for templates because those have names but should be recursively searched, not returned.
                        return tokenStartIndex, tokenEndIndex, token
                
                #token not found, update search index position and continue
                if forwardDecode: searchIndexPostion = tokenEndIndex
                else: searchIndexPosition = tokenStartIndex
                continue
            else:   #token has unbounded size
                if forwardDecode:
                    tokenStartIndex = searchIndexPosition
                    tokenEndIndex = primaryPassSearchIndexPosition    #token is unbounded, so ends at packet end
                else:
                    tokenStartIndex = primaryPassSearchIndexPosition #going in reverse, so start is beginning of packet
                    tokenEndIndex = searchIndexPosition
                    
                if type(token) == template or type(token) == packetTemplate:
                    searchStartIndex, searchEndIndex, searchToken = token.findTokenPosition(tokenName, workingPacket[tokenStartIndex:tokenEndIndex], forwardDecode)
                    tokenEndIndex = tokenStartIndex + searchEndIndex
                    tokenStartIndex += searchStartIndex
                    if searchToken != None: # Token found in embedded template
                        return tokenStartIndex, tokenEndIndex, searchToken
                else: #not a template
                    if token.keyName == tokenName: #Found!
                        return tokenStartIndex, tokenEndIndex, token
        
        #No token found!
        return 0, packetLength, None # return indices for the entire input packet
                    
                                                    
        

class packetToken(object):
    """Base class for creating packet tokens, which are elements that handle encoding and decoding each segment of a packet."""
    
    def __init__(self, keyName, *args):
        """Initialize a new packet token.
        
        keyName -- a reference name for the token that will match a key in an encoding dictionary, or be provided as a key during decoding.
        """
        self.keyName = keyName  # permanently store keyName
        self.parentTemplateName = ""    #used for error output, this gets updated by the parent template upon its instantiation.
        self.requireEncodeDict = True   #by default, tokens require an encode dictionary in order to encode packets. Exceptions include length and checksum tokens.
        self.size = 0   # by default, tokens encode to and decode from a list of predetermined size. Exceptions incude pList, pString, and packet tokens.
                        # size = 0 means it has no predetermined size, which is a fail-safe default for validation.
        self.init(*args)    # call subclass init function to do something with additional arguments.
    
    def init(self, *args):
        """Secondary initializer should be over-ridden by subclass.""" 
        pass
    
    def encode(self, encodeDict, inProcessPacket = []):
        """Serializes the value keyName in encodeDict using the subclass's _encode_ method.
        
        encodeDict -- a dictionary of values to be encoded. Only the value who's key matches keyName will be encoded by the method.
        inProcessPacket -- whatever has already been processed. Only used by post-processing tokens like length and checksums. 
        """
        if self.keyName in encodeDict:  # keyName has a matching value in the encodeDict, proceed!
            return self._encode_(encodeDict[self.keyName], inProcessPacket) # call the subclass's _encode_ method for token-specific processing.
        elif self.requireEncodeDict: # no keyName has been found and dictionary required, so compose a useful error message and raise an exception.
            if self.parentTemplateName: errorMessage = str(self.keyName) + " not found in template " + self.parentTemplateName + "."
            else: errorMessage = str(self.keyName) + " not found in template."
            raise KeyError(errorMessage)
        else: return self._encode_(None, inProcessPacket)   #some tokens don't require an entry in the encode dictionary
        
    def decode(self, inputPacket, forwardDecode = True):
        """Extracts relevant bytes from a packet and converts into a key:value pair using the sublcass's _decode_ method.
        
        inputPacket -- the list of bytes from which to extract the information represented by the token.
        forwardDecode -- if true, remove bytes from beginning of packet (left side), otherwise remove from the right.
        
        Each token will remove a quantity of bytes from the inputPacket and decode into a value. For tokens with fixed
        size, a fixed number of bytes will be removed. If the size is unbounded then the entire packet will be consumed.
        """
        #break apart input packet here to keep from repeating that work in every token
        if self.size > 0:   #fixed size
            if forwardDecode:   #working from the front of the inputPacket
                decodePacket = inputPacket[:self.size]
                remainingPacket = inputPacket[self.size:]
            else:   #working from the back of the inputPacket
                decodePacket = inputPacket[-self.size:]
                remainingPacket = inputPacket[:-self.size]
        else: #size is unbounded
            decodePacket = inputPacket
            remainingPacket = []
            
        decodedValue = self._decode_(decodePacket)
        
        return {self.keyName:decodedValue}, remainingPacket


#---- TOKEN TYPES ----

class unsignedInt(packetToken):
    """An unsigned integer token type."""
    
    def init(self, size):
        """Initializes the unsigned integer token.
        
        size -- the length in bytes of the unsigned integer.
        """
        self.size = size # length of unsigned integer
    
    def _encode_(self, encodeValue, inProcessPacket):
        """Converts an unsigned integer into a sequence of bytes.
        
        encodeValue -- contains an unsigned integer.
        """
        return utilities.unsignedIntegerToBytes(encodeValue, self.size)
    
    def _decode_(self, decodePacket):
        """Decodes the provided packet snippet into an unsigned integer.
        
        decodePacket -- the ordered list of bytes to be converted into an unsigned integer.
        """
        return utilities.bytesToUnsignedInteger(decodePacket)


class length(packetToken):
    """A length-of-packet integer token type."""
    def init(self, size = 1, countSelf = False):
        """Initializes the length token.
        
        size -- the length in bytes of the token
        countSelf -- if true, the length byte will be counted
        """
        self.size = size
        self.countSelf = countSelf
        self.requireEncodeDict = False  #does not require an encode dictionary, because input is the entire in-process packet
    
    def _encode_(self, encodeValue, inProcessPacket):
        """Returns the length of the inProcessPacket, either including or nor itself.
        
        inProcessPacket -- contains a second-pass in-process packet whose length should be measured.
        
        NOTE: This assumes that there are not multiple length tokens in a single packet.
        """
        
        if len(inProcessPacket)>0:  #an inProcess packet has been provided
            #create and count a list only containing integers from the flattened inProcessPacket
            length = len(list(itertools.ifilter(lambda token: type(token) == int, utilities.flattenList(inProcessPacket))))
            if self.countSelf: length += 1
            return utilities.unsignedIntegerToBytes(length, self.size)  #convert to integer of lenth self.size
        else: return self   #no in-process packet has been provided.
    
    def _decode_(self, decodePacket):
        """Decodes the provided packet snippet into an unsigned integer ostensibly representing a length.
        
        decodePacket -- the ordered list of bytes to be converted into an unsigned integer.
        
        Note that no length validation is performed here.
        """
        return utilities.bytesToUnsignedInteger(decodePacket)
        

class checksum(packetToken):
    """Performs a checksum operation on the in-process packet."""
    def init(self, polynomial = 7):
        """Initializes the checksum token.
        
        polynomial -- defines the taps used to generate a CRC value. For Gestalt, this defaults to 7 (ATM standard)
        """
        self.CRCInstance = utilities.CRC(polynomial)    # initialize a CRC gen/test class
        self.requireEncodeDict = False  #doesn't need an input from the encode dictionary
        self.size = 1   #for now only supports single-byte checksums
    
    def _encode_(self, encodeValue, inProcessPacket):
        """Returns the checksum value of the in-process packet.
        
        inProcessPacket -- contains a third-pass in-process packet whose checksum should be computed.
        """
        
        if len(inProcessPacket)>0: #an inProcess packet has been provided
            # create list of all the ints. At this point that should be everything but the checksum token
            checksumList = list(itertools.ifilter(lambda token: type(token) == int, utilities.flattenList(inProcessPacket)))
            return self.CRCInstance.generate(checksumList)  #generate and return checksum
        else: return self
        
    def _decode_(self, decodePacket):
        """Decodes the provided packet snippet into an unsigned integer ostensibly representing a checksum.
        
        decodePacket -- the ordered list of bytes to be converted into an unsigned integer.
        
        Note that no checksum validation is performed here.
        """
        return utilities.bytesToUnsignedInteger(decodePacket)


class pList(packetToken):
    """A list-type token.
    
    Note that if no length is provided, whatever list is provided will be passed thru.
    """
    def init(self, size = 0):
        """Initializer for pList token type."""
        self.size = size  # if 0, length is determined by the run-time input to the encoder or decoder
    
    def _encode_(self, encodeValue, inProcessPacket):
        """Inserts the list provided in encodeValue into the packet.
        
        encodeValue -- contains the list to be inserted.
        """
        return encodeValue

    def _decode_(self, decodePacket):
        """Decodes the provided packet snippet into a list.
        
        This decode function is super easy. Because its size is unbounded, it returns exactly what was fed into it.
        """
        return decodePacket


class pString(packetToken):
    """A string-type token.
    
    Note that if no length is provided, whatever string is provided will be converted to a list and passed thru.
    """
    def init(self, size = 0):
        """Initializer for pString token type."""
        self.size = size  # if 0, length is determined by the run-time input to the encoder or decoder
        
    def _encode_(self, encodeValue, inProcessPacket):
        """Converts string into a list.
        
        encodeValue -- contains the string to be converted and inserted.
        """
        return utilities.stringToList(encodeValue)
    
    def _decode_(self, decodePacket):
        """Decodes the provided packet snippet into a string.
        
        decodePacket -- the list to be converted into a string.
        """
        return utilities.listToString(decodePacket)


class packet(packetToken):
    """An embedded packet.
    
    Note that this is similar to the pList token except that it converts a packet into a list on encode.
    The primary reason for breaking out out is to make embedded packets more explicit in the template definition.
    """
    def init(self):
        """Initializer for packet token type."""
        self.size = 0  # length is determined by the runt-time input to the encoder or decoder
        
    def _encode_(self, encodeValue, inProcessPacket):
        """Converts sub-packet to list, and insert into packet.
        
        encodeValue -- contains a packets.packet instance.
        """
        return list(encodeValue)
    
    def _decode_(self, decodePacket):
        """Decodes the provided packet snippet into a packets.serializedPacket object.
        
        decodePacket -- the list to be converted into a serializd packet object.
        """
        return serializedPacket(decodePacket)


class packetTemplate(packetToken):
    """A nested packet template.
    
    The primary use of this token type is to extend a packet definition.
    """
    def init(self, template):
        """Initializes packet template token.
        
        template -- a packets.template instance.
        
        This token is a direct pass-thru to the child template, and is provided for legibility.
        """
        self.template = template
        self.size = self.template.size    #inherits fixed size from child template
        self.requireEncodeDict = False  #This token is just a pass-thru to the template
    
    def encode(self, encodeDict):
        """Encodes the nested packet template using the provided encoding dictionary.
        
        encodeDict -- contains the encoding dictionary to be encoded by the template.
        """
        return self.template.encode(encodeDict)

    def decode(self, inputPacket, forwardDecode):
        """Decodes child template by passing along decode call.
        
        Unlike most packet tokens, this one overrides the parent class's decode method.
        """
        return self.template.decode(inputPacket, forwardDecode)
    
    def findTokenPosition(self, tokenName, inputPacket, forwardDecode = True):
        """Returns the index range that a referenced token spans in the input packet.
        
        As with the other functions in this class, just forwards the request on to the child template.
        """
        return self.template.findTokenPosition(tokenName, inputPacket, forwardDecode)

class signedInt(packetToken):
    """A signed integer token."""
    def init(self, size = 1):
        """Initializer for signed integer token.
        
        size -- the length in bytes of the signed integer. Note that max value is +/- 0.5*size.
        """
        self.size = size
        
    def _encode_(self, encodeValue, inProcessPacket):
        """Encodes the provided value into a signed integer fit within the specified number of bytes.
        
        encodeValue -- the signed integer to be encoded.
        """
        twosComplementRepresentation = utilities.signedIntegerToTwosComplement(encodeValue, self.size)  #note that function handles both pos and neg numbers.
        return utilities.unsignedIntegerToBytes(twosComplementRepresentation, self.size) # convert to byte list.

    def _decode_(self, decodePacket):
        """Decodes the provided packet snippet into a signed integer of length self.size.
        
        decodePacket -- the ordered list of bytes to be converted into an unsigned integer.
        """
        twosComplementInteger = utilities.bytesToUnsignedInteger(decodePacket)
        return utilities.twosComplementToSignedInteger(twosComplementInteger, self.size)
           

class fixedPoint(packetToken):
    """A signed fixed point decimal token."""
    def init(self, integerBits, fractionalBits):
        """Initializer for signed fixed point decimal tokens.
        
        integerBits -- number of integer bits. X in X.Y
        fractionalBits -- number of fractionalBits. Y in X.Y.
        
        Note that integerBits + fractionalBits will be packed into the smallest possible number of bytes.
        Ideally integerBits + fractionalBits + 1 (sign bit) is divisible by 8.
        """
        self.integerBits = integerBits
        self.fractionalBits = fractionalBits
        self.size = int(math.ceil((integerBits + fractionalBits)/8.0))   #smallest number of bytes that will contain the fixed-point format.
    
    def _encode_(self, encodeValue, inProcessPacket):
        """Encodes the provided value into a signed fixed-point decimal."""
        
        bitShiftedValue = encodeValue * 2**self.fractionalBits   #fixed-point encoding is as simple as left-shifting by the fractional bits.
        twosComplementRepresentation = utilities.signedIntegerToTwosComplement(int(bitShiftedValue), self.size) # convert to twos complement
        return utilities.unsignedIntegerToBytes(twosComplementRepresentation, self.size)    #convert to byte list
        
    def _decode_(self, decodePacket):
        """Decodes the provided packet snippet into a fixed point signed decimal.
        
        decodePacket -- the ordered list of bytes to be converted into a fixed point decimal.
        """
        twosComplementRepresentation = utilities.bytesToUnsignedInteger(decodePacket)
        signedInteger = utilities.twosComplementToSignedInteger(twosComplementRepresentation, self.size)
        bitShiftedValue = float(signedInteger)/(2**self.fractionalBits)
        return bitShiftedValue