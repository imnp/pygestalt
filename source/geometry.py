#   pyGestalt Geometry Module

"""A library for expressing and manipulating geometry."""

import math
from pygestalt import errors

class array(list):
    """A container for storing multi-dimensional arrays of numbers.
    
    Arrays are simply sub-classes of lists, but include functionality for indexing and printing.
    """
    def __init__(self, arrayList):
        """Initialization function for the array object.
         
        arrayList -- a list of the format [[a1, a2, ..., aN], [b1, b2, ..., bN], ..., [z1, z2, ..., zN]],
                     or an array or matrix.
                      
        Note that contents of the array cannot be a list, or else they will be confused with a dimension of the array.
        """
        super(array, self).__init__(arrayList)

    def getSize(self):
        """Returns the size of the array.
        
        The size of the array is returned as a tuple e.g. (x, y, z, ...), where:
            x -- number of rows
            y -- number of columns
            z -- further dimension within each cell
        """
        
        workingCopy = list(self) #avoids calling self.__getitem__
        sizeTuple = ()
        while type(workingCopy) == list: #drills down array until encounters item that's not a list
            sizeTuple += (len(workingCopy),)
            workingCopy = workingCopy[0]
        
        return sizeTuple
        

    def getDimension(self):
        """Returns the dimension of the array.
        
        The dimension of the array is defined as the number of nested lists.
        """
        return len(self.getSize())
    
    def __str__(self):
        return "(pyGestalt " + type(self).__name__.capitalize() + ") "+ str(list(self)) 
        
    def __getitem__(self, positionTuple, subArray = None):
        """Returns an individual item or a slice in the array.
        
        positionTuple -- this is provided by the Python interpreter when the array is indexed
        subArray -- this is only used internally for the recursive algorithm
        
        To index into a specific cell of an array, simply index as myArray[1,2] to retrieve item in row 1, column 2.
        To index an entire subarray, index as myArray[1,:] to retrieve all of row 1.
        If the number of indices in positionTuple is less than the dimensionality of the array,
            and if no slices are used, then indexing starts at the first dimension whose size is greater than 1.
            This is to support compatibility between various formats of arrays, i.e. a 1D array and a 2D 1xN array.
        """
        if type(positionTuple) != tuple: positionTuple = (positionTuple,) #catches condition when only one index is provided
        
        if subArray == None: #starting the algorithm
            subArray = list(self) #need to convert to a list to avoid a circular reference
            
            arraySize = self.getSize() #a tuple containing the sizes of each dimension of the array
            arrayDimension = self.getDimension()
            
            if type(positionTuple[-1]) != slice and len(positionTuple) < arrayDimension:
                #the requested index is smaller than the array dimension and isn't requesting a slice at the end
                #try to increase dimensionality of position tuple to match array, to the extent that the array is
                #    excessively dimensional (i.e. an index of (x,) into a 1xN array.
                for size in arraySize:
                    if size == 1:
                        positionTuple = (0,) + positionTuple
                    else:
                        break
                
                if len(positionTuple) != arrayDimension:
                    raise errors.ArrayError("Index Error - array is larger than indices provided, and cannot minimize array to match.")
        
        positionIndex = positionTuple[0]
        positionRemainder = positionTuple[1:]
        
        if type(positionIndex) == slice: #asking for an array slice
            if positionRemainder == (): #user didn't ask for more than the slice... good!
                return type(self)(subArray)
            else:
                slicedArrayList = [self.__getitem__(positionRemainder, arraySlice) for arraySlice in subArray]
                return type(self)(slicedArrayList)
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



class matrix(array):
    """A matrix object that extends the array type with mathematical operations.
    
    While matrix is a subclass of array, note that matrices MUST have a dimensionality of 2.
    """

    def __init__(self, arrayList):
        """Initialization function for the matrix object.
        
        arrayList -- a list of the format [[a1, a2, ..., aN], [b1, b2, ..., bN], ..., [z1, z2, ..., zN]].
                     MUST be of dimensionality 2. If a 1-D array is provided (i.e. a list), it will be wrapped.
        
        Note that contents of the array cannot be a list, or else they will be confused with a dimension of the array.
        """
        
        if type(arrayList) != list: #check for correct input
            raise errors.MatrixError("Matrix must be created with a list-formatted array. E.g. [[a1,a2],[b1,b2]]")
            return False
        
        inputDimension = self.getListDimensionality(arrayList) #determine the dimensionality of the input list
        
        if inputDimension > 2: #dimensionality is too big for a matrix.
            raise errors.MatrixError("Matrix must have dimensionality <=2. Input has dimensionality of "+ str(inputDimension))
            return False
        if inputDimension == 1:
            arrayList = [arrayList] #wrap array to get dimensionality of 2
        super(matrix, self).__init__(arrayList)
            
    def transpose(self):
        """Returns the transpose of the matrix."""
        rows = self.size[0]
        columns = self.size[1]
        return matrix([[self[row, column] for row in range(rows)] for column in range(columns)])
    
    def __mul__(self, otherMatrix):
        """Matrix multiply.
        
        otherMatrix -- a matrix by which to multiply.
        """
        leftSize = self.size
        rightSize = otherMatrix.size
        
        leftRows = leftSize[0]
        leftColumns = leftSize[1]
        rightRows = rightSize[0]
        rightColumns = rightSize[1]
        
        if leftColumns == rightRows: #arrays can be multiplied
            return matrix([[dotProduct(self[leftRow,:], otherMatrix[:,rightColumn].transpose()) for rightColumn in range(rightColumns)] for leftRow in range(leftRows)])

    def __str__(self):
        return "(pyGestalt Matrix) "+ str(self.arrayList)            
    
def dotProduct(array1, array2):
    """Returns the dot product of two arrays.
    
    array1, array2 -- the input arrays. For now, these are expected to be matching 1D arrays.
    
    Returns array1 *dot* array2
    """
    
    runningDotProduct = 0
    for index in range(array1.size[0]):
        runningDotProduct += array1[index]*array2[index]
    return runningDotProduct