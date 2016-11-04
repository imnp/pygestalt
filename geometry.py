#   pyGestalt Geometry Module

"""A library for expressing and manipulating geometry."""

import math
from pygestalt import errors

class array(object):
    """A container for storing multi-dimensional arrays of numbers."""   
    def __init__(self, arrayList):
        """Initialization function for the array object.
        
        arrayList -- a list of the format [[a1, a2, ..., aN], [b1, b2, ..., bN], ..., [z1, z2, ..., zN]]
        
        Note that contents of the array cannot be a list, or else they will be confused with a dimension of the array.
        """
        self.arrayList = arrayList
        self.size = self.getSize() #calculates the size of the array
    
    def getSize(self, subArray = None):
        """Returns the size of the array.
        
        subArray -- DO NOT PROVIDE EXTERNALLY. This is used internally.
                    if None, self.arrayList is used
                    
        The size of the array is returned as a tuple e.g. (x, y, z, ...), where:
            x -- number of rows
            y -- number of columns
            z -- further dimension within each cell
        """
        if subArray == None: #starting the algorithm
            subArray = self.arrayList
        
        if type(subArray) != list: #at the end of the recursion
            return ()
        else:
            return (len(subArray),) + self.getSize(subArray[0])
        
    def __getitem__(self, positionTuple, subArray = None):
        """Returns an individual item or a slice in the array.
        
        positionTuple -- this is provided by the Python interpreter when the array is indexed
        subArray -- this is only used internally for the recursive algorithm
        
        To index into a specific cell of an array, simply index as myArray[1,2] to retrieve item in row 1, column 2.
        To index an entire subarray, index as myArray[1,:] to retrieve all of row 1.
        """
        
        if subArray == None: #starting the algorithm
            subArray = self.arrayList
        
        if type(positionTuple) != tuple: positionTuple = (positionTuple,) #catches condition when only one index is provided
        
        positionIndex = positionTuple[0]
        positionRemainder = positionTuple[1:]
        
        if type(positionIndex) == slice: #asking for an array slice
            if positionRemainder == (): #user didn't ask for more than the slice... good!
                return array(subArray)
            else:
                slicedArrayList = [self.__getitem__(positionRemainder, arraySlice) for arraySlice in subArray]
                return array(slicedArrayList)
        else: #asking for an indexed value:
            try:
                indexedValue = subArray[positionIndex]
            except:
                raise errors.ArrayError("Index Error - index out of bounds of array")
                return False
            
            if type(indexedValue) == list: #need to index deeper into the array
                if positionRemainder == (): #no index provided!
                    raise errors.ArrayError("Index Error - array is larger than number of indices provided")
                    return False
                else:
                    return self.__getitem__(positionRemainder, indexedValue)
            else: #end of array
                if positionRemainder == (): #no extra indices requested, good!
                    return indexedValue #finally return the value
                else:
                    raise errors.ArrayError("Index Error - array is smaller than number of indices provided")
                    return False
    
    def __str__(self):
        return "(pyGestalt Array) "+ str(self.arrayList)
