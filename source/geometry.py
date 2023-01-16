#   pyGestalt Geometry Module

"""A library for expressing and manipulating geometry."""

import math
from pygestalt import errors, units

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
        return arraySize(self)
        
        
    def getDimension(self):
        """Returns the dimension of the array.
        
        The dimension of the array is defined as the number of nested lists.
        """
        return arrayDimension(self)

    
    def __str__(self):
        return "(pyGestalt " + type(self).__name__.capitalize() + ") "+ str(list(self)) 

        
    def __getitem__(self, positionTuple):
        """Returns an individual item or a slice in the array.
        
        positionTuple -- this is provided by the Python interpreter when the array is indexed
        
        This method over-rides the built-in __getitem__ method of the list type.
        To index into a specific cell of an array, simply index as myArray[1,2] to retrieve item in row 1, column 2.
        To index an entire subarray, index as myArray[1,:] to retrieve all of row 1.
        If the number of indices in positionTuple is less than the dimensionality of the array,
            then indexing starts at the first dimension whose size is greater than 1.
            This is to support compatibility between various formats of arrays, i.e. a 1D array and a 2D 1xN array.
        
        If the returned value is a list-formatted array, it will be returned as the same type as this object. Note
        that because the array type can be sub-classed, the returned object may be a matrix, etc...
        """
        
        returnValue =  indexIntoArray(self, positionTuple)
        
        if isinstance(returnValue, list): #if the returned value is a list-formatted array, return it as an object of this type.
            returnValue = type(self)(returnValue)

        return returnValue
    
    def __getslice__(self, start, stop):
        """Depreciated method for handling single slice __getitem__ requests."""
        return self.__getitem__(slice(start, stop, None))
    
    def __add__(self, otherArray):
        """Overrides left-hand addition to perform piece-wise addition of arrays.
        
        otherArray -- a list-formatted array to add to this array.
        
        returns a new array [b0, b1,..., bn] where b0 = self[0] + otherArray[0]
        """
        return type(self)(arrayAddition(self, otherArray))
    
    def __radd__(self, otherArray):
        """Overrides right-hand addition to perform piece-wise addition of arrays.
        
        otherArray -- a list-formatted array to add to this array.
        
        returns a new array [b0, b1,..., bn] where b0 = otherArray[0] + self[0]
        """
        return type(self)(arrayAddition(otherArray, self))

    def __sub__(self, otherArray):
        """Overrides left-hand subtraction to perform piece-wise subtraction of arrays.
        
        otherArray -- a list-formatted array to subtract from this array.
        
        returns a new array [b0, b1,..., bn] where b0 = self[0] - otherArray[0]
        """
        return type(self)(arraySubtraction(self, otherArray))
    
    def __rsub__(self, otherArray):
        """Overrides right-hand subtraction to perform piece-wise subtraction of arrays.
        
        otherArray -- a list-formatted array from which to subtract this array.
        
        returns a new array [b0, b1,..., bn] where b0 = otherArray[0] - self[0]
        """
        return type(self)(arraySubtraction(otherArray, self))
        


class matrix(array):
    """A matrix object that extends the array type with mathematical operations.
     
    While matrix is a subclass of array, note that matrices MUST have a dimensionality of 2.
    """
          
    def __init__(self, arrayList):
        """Instantiation function for the matrix object.
         
        arrayList -- a list of the format [[a1, a2, ..., aN], [b1, b2, ..., bN], ..., [z1, z2, ..., zN]].
                     MUST be of dimensionality 2. If a 1-D array is provided (i.e. a list), it will be wrapped.
         
        Note that contents of the array cannot be a list, or else they will be confused with a dimension of the array.
        """
         
        if not isinstance(arrayList, list): #check for correct input
            raise errors.MatrixError("Matrix must be created with a list-formatted array. E.g. [[a1,a2],[b1,b2]]")
            return False

        super(matrix, self).__init__(arrayList)
                          
        inputDimension = self.getDimension() #determine the dimensionality of the input list
          
        if inputDimension > 2: #dimensionality is too big for a matrix.
            raise errors.MatrixError("Matrix must have dimensionality <=2. Input has dimensionality of "+ str(inputDimension))
            return False
        if inputDimension == 1:
            arrayList = [list(arrayList)] #wrap array to get dimensionality of 2
            super(matrix, self).__init__(arrayList) #call __init__ again to perform the wrap

    def transpose(self):
        """Returns the transpose of the matrix."""
        return matrix(matrixTranspose(self))
    
    def determinant(self, subMatrix = None):
        """Returns the determinant of the matrix. """
        return self._determinant_()
    
    def concatenateRight(self, rightMatrix):
        """Returns a new matrix with the provided matrix concatenated to the right."""
        return matrix(matrixHorizontalConcatenate(self, rightMatrix))
    
    def concatenateLeft(self, leftMatrix):
        """Returns a new matrix with the provided matrix concatenated to the left."""
        return matrix(matrixHorizontalConcatenate(leftMatrix, self))
    
    def inverse(self):
        """Returns the inverse of the matrix."""
        return matrix(matrixInverse(self))

    def __mul__(self, otherMatrix):
        """Matrix multiply.
         
        otherMatrix -- a matrix or scalar by which to multiply.
        """
        
        if isinstance(otherMatrix, list):
            return matrix(matrixMultiply(self, otherMatrix))
        else:
            return matrix(arrayMultiplyByScalar(self,otherMatrix))

    def __pow__(self, power):
        """Matrix inversion.
        
        power -- the degree to which to raise the matrix.
        
        """
        if power == 1:
            return self
        elif power == -1:
            return self.inverse()
        else:
            raise errors.MatrixError("Cannot raise matrix to " + str(power) + " power. Can only invert by raising to -1.")
            return False

def identityMatrix(size):
    """Returns an identity matrix with 1s across the diagonal.
    
    size -- the size of the matrix.
    """
    
    return matrix([[1.0 if horizontalIndex == verticalIndex else 0.0 for horizontalIndex in range(size)] for verticalIndex in range(size)])

#--- ARRAY HELPER FUNCTIONS ---
def arraySize(inputArray):
    """Returns the size of a list-formatted array.
    
    The size of inputArray is returned as a tuple e.g. (x, y, z, ...), where:
        x -- number of rows
        y -- number of columns
        z -- further dimension within each cell
    """
    
    sizeTuple = ()
    while isinstance(inputArray, list): #drills down array until encounters item that's not a list
        sizeTuple += (len(inputArray),)
        try:
            inputArray = list.__getitem__(inputArray, 0) #avoid calling __getitem__ of array b/c it may have multi-dimensional index behavior
        except IndexError: #array is empty, but still has a size
            inputArray = None
    return sizeTuple

def arrayDimension(inputArray):
    """Returns the dimension of a list-formatted array.
    
    The dimension of the array is defined as the number of nested lists.
    """
    return len(arraySize(inputArray)) #simply return the length of the size tuple.

def indexIntoArray(inputArray, indexTuple):
    """Returns an individual item or a slice in a list-formatted array.
    
    inputArray -- a list-formatted array for which a particular index is to be retrieved.
    indexTuple -- a tuple providing indexes into the array, which may be values or slices. The length of
                     the tuple must match the dimensionality of the array, STARTING FROM THE FIRST DIMENSION WHOSE
                     SIZE IS GREATER THAN 1.
    
    To index into a specific cell of an array, simply index as myArray[1,2] to retrieve item in row 1, column 2.
    To index an entire subarray, index as myArray[1,:] to retrieve all of row 1.
    To index a partial space of the array, index as myArray[1:,1:] to retrieve the lower right corner of the array.
    If the number of indices in indexTuple is less than the dimensionality of the array, indexing will be left-justified to
        the first dimension with a size greater than 1 within the bounds of the dimensionality of the array.
        For example, if an array [[1,2,3]] is indexed as [0], 1 will be returned. But if [[1,2],[3,4]] is indexed as [0],
        [1,2] will be returned because there are no dimensions whose size is 1.
    """
    
    #catch condition when only one index is provided, as the algorithm expects the indexTuple as a tuple
    if type(indexTuple) != tuple: indexTuple = (indexTuple,)
    
    #check if array has more dimensions than indices provide.
    inputArraySize = arraySize(inputArray)
    if len(inputArraySize) > len(indexTuple): #Ignore as many initial dimensions with a size of 1 as possible.
        possibleDimensionsToIgnore = inputArraySize[:(len(inputArraySize)-len(indexTuple))]
        dimensionsToIgnore = ()
        for dimension in possibleDimensionsToIgnore:
            if dimension == 1:
                dimensionsToIgnore += (0,)
            else:
                break

        indexTuple = dimensionsToIgnore + indexTuple
    
    if len(indexTuple) == 0: #no indices provided, must be an error
        raise errors.ArrayError("Index Error - not enough indices provided to index array.")
        return False
    
    elif len(indexTuple) == 1: #exactly 1 index provided, so index directly into the inputArray using list.__getitem__
        return list.__getitem__(inputArray, indexTuple[0])
    
    else: #more than 1 index provided after this, so return a recursively derived array
        if type(indexTuple[0]) != slice: #only one item requested, so dig deeper
            return indexIntoArray(list.__getitem__(inputArray, indexTuple[0]), indexTuple[1:])
        
        else: #a slice was provided, so build up a return array
            returnArray = [] #seed for building up a return array
            for index in range(len(inputArray))[indexTuple[0]]:
                returnValue = indexIntoArray(list.__getitem__(inputArray, index), indexTuple[1:])
                if not isinstance(returnValue, list):
                    returnValue = [returnValue]
                returnArray += [returnValue]

            return returnArray    

#--- ARRAY MATH FUNCTIONS ---
def dotProduct(array1, array2):
    """Returns the dot product of two matrices.
    
    array1, array2 -- the input arrays. For now, these are expected to be matching 1D or 2D 1xN arrays.
    
    Returns array1 *dot* array2
    """
    
    runningDotProduct = 0
    for index in range(array1.getSize()[-1]): #takes the last index as the anticipation is that the array is either 1D or 1xN
        runningDotProduct += array1[index]*array2[index]
    return runningDotProduct

def arrayMultiplyByScalar(inputArray, scalar):
    """Multiplies each value in an input array by a scalar.
    
    inputArray -- a list-formatted array or matrix. For the purposes of recursion, inputArray is allowed to also be a scalar.
    scalar -- the value by which to multiply each value of the array.
    """
    if isinstance(inputArray, list):
        return [arrayMultiplyByScalar(arrayItem, scalar) for arrayItem in inputArray]
    else:
        return inputArray*scalar

def arrayAddition(leftArray, rightArray):
    """Performs piece-wise addition of elements in two input arrays.
    
    leftArray, rightArray -- the two arrays to add. For the purposes of recursion, these are also allowed to be scalars.
    """
    if isinstance(leftArray, list):
        return [arrayAddition(*arrayItems) for arrayItems in zip(leftArray, rightArray)]
    else:
        return leftArray + rightArray

def arraySubtraction(leftArray, rightArray):
    """Performs piece-wise subtraction of elements in two input arrays.
    
    leftArray, rightArray -- the two arrays to perform the subtraction. For the purposes of recursion, these are also allowed to be scalars.
    
    Returns leftArray - rightArray
    """
    if isinstance(leftArray, list):
        return [arraySubtraction(*arrayItems) for arrayItems in zip(leftArray, rightArray)]
    else:
        return leftArray - rightArray


    
def matrixTranspose(inputMatrix):
    """Returns the transpose of a matrix.
    
    inputMatrix -- a 2D list-formatted array to transpose
    
    Returns the transpose of the matrix as a list-formatted array
    """
    try:
        rows, columns = arraySize(inputMatrix)
    except:
        raise errors.MatrixError("Cannot perform matrix transpose. Input must be provided as a 2D array!")
        return False
    
    return [[inputMatrix[row, column] for row in range(rows)] for column in range(columns)]

def matrixMultiply(leftMatrix, rightMatrix):
    """Performs a matrix multiplication of leftMatrix*rightMatrix.

    leftMatrix, rightMatrix: the two matrices to be multiplied. These must be provided as list-formatted matrices.
    """
    try:
        leftRows, leftColumns = arraySize(leftMatrix)
        rightRows, rightColumns = arraySize(rightMatrix)
    except:
        raise errors.MatrixError("Cannot multiply matrices. Input must be provided as a 2D array!")
        return False        
     
    if leftColumns == rightRows: #arrays can be multiplied
        return [[dotProduct(leftMatrix[leftRow,:], rightMatrix[:,rightColumn].transpose()) for rightColumn in range(rightColumns)] for leftRow in range(leftRows)]   
    else:
        raise errors.MatrixError("Cannot multiply matrices because the numbers of columns of the left matrix don't equal the number of rows of the right matrix ")
        
    
def matrixDeterminant(inputMatrix):
    """Returns the determinant of a matrix.
    
    inputMatrix -- a 2D SQUARE list-formatted array representing the matrix
    
    Note that this is a recursive algorithm.
    """
    try:
        rows, columns = arraySize(inputMatrix)
    except:
        raise errors.MatrixError("Cannot take matrix determinant. Input must be provided as a 2D array!")
        return False
    
    if rows != columns:
        raise errors.MatrixError("Cannot take matrix determinant. 2D input matrix must be square.")
        return False
    
    elif rows == 1:
        raise errors.MatrixError("Cannot take matrix determinant. Input matrix must be at least 2x2.")
        return False
    
    elif rows == 2: #2x2 matrix was provided. Return specific 2D determinant to save some time.
        # det[[a,b],[c,d]] = a*d - b*c
        a = indexIntoArray(inputMatrix, (0,0))
        b = indexIntoArray(inputMatrix, (0,1))
        c = indexIntoArray(inputMatrix, (1,0))
        d = indexIntoArray(inputMatrix, (1,1))
        return a*d - b*c
    
    else: #matrix is larger than 2x2
        topRow = indexIntoArray(inputMatrix, (0, slice(None))) #get top row
        bottomRows = indexIntoArray(inputMatrix, (slice(1,None), slice(None)))
        
        runningDeterminant = 0 #keeps track of running value of determinant

        for index in range(len(topRow)):
            singleValue = topRow[index]
            
            leftColumns = indexIntoArray(bottomRows, (slice(None), slice(None, index)))
            rightColumns = indexIntoArray(bottomRows, (slice(None), slice(index+1, None)))
            
            subMatrix = matrixHorizontalConcatenate(leftColumns, rightColumns)
            subMatrixDeterminant = matrixDeterminant(subMatrix)
            
            runningDeterminant += singleValue*subMatrixDeterminant*((-1)**index)
        
        return runningDeterminant

def matrixInverse(inputMatrix):
    """Returns the inverse of an matrix, or None if no inverse exists.
    
    inputMatrix -- a list-formatted 2D SQUARE matrix whose inverse is to be found.
    """
    try:
        rows, columns = arraySize(inputMatrix)
    except:
        raise errors.MatrixError("Cannot take matrix inverse. Input must be provided as a 2D array!")
        return False
    
    if rows != columns:
        raise errors.MatrixError("Cannot take matrix inverse. 2D input matrix must be square.")
        return False
    
    if rows > 3:
        raise errors.MatrixError("Cannot take inverse of " + str(rows)+ "x" + str(rows) + " matrix. Only 2x2 and 3x3 matrices are currently supported.")
        return False
    
    det = matrixDeterminant(inputMatrix)
    if det == 0: return None #matrix is not invertible
    
    if rows == 2: #2x2 matrix
        a = indexIntoArray(inputMatrix, (0,0))
        b = indexIntoArray(inputMatrix, (0,1))
        c = indexIntoArray(inputMatrix, (1,0))
        d = indexIntoArray(inputMatrix, (1,1))
        
        return arrayMultiplyByScalar([[d, -b],[-c, a]], 1.0/det)
    
    if rows == 3:
        #need to find [[a,b,c],[d,e,f],[g,h,i]]
        a = indexIntoArray(inputMatrix, (slice(1,None), slice(1,None)))
        c = indexIntoArray(inputMatrix, (slice(None,2), slice(1, None)))
        g = indexIntoArray(inputMatrix, (slice(1, None), slice(None,2)))
        i = indexIntoArray(inputMatrix, (slice(None, 2), slice(None, 2)))
        
        b0 = indexIntoArray(inputMatrix, (0,2))
        b1 = indexIntoArray(inputMatrix, (0,1))
        b2 = indexIntoArray(inputMatrix, (2,2))
        b3 = indexIntoArray(inputMatrix, (2,1))
        b = [[b0, b1], [b2, b3]]
        
        d0 = indexIntoArray(inputMatrix, (1,2))
        d1 = indexIntoArray(inputMatrix, (1,0))
        d2 = indexIntoArray(inputMatrix, (2,2))
        d3 = indexIntoArray(inputMatrix, (2,0))
        d = [[d0, d1], [d2, d3]]
        
        e0 = indexIntoArray(inputMatrix, (0,0))
        e1 = indexIntoArray(inputMatrix, (0,2))
        e2 = indexIntoArray(inputMatrix, (2,0))
        e3 = indexIntoArray(inputMatrix, (2,2))
        e = [[e0, e1], [e2, e3]]
        
        f0 = indexIntoArray(inputMatrix, (0,2))
        f1 = indexIntoArray(inputMatrix, (0,0))
        f2 = indexIntoArray(inputMatrix, (1,2))
        f3 = indexIntoArray(inputMatrix, (1,0))
        f = [[f0, f1],[f2, f3]]
        
        h0 = indexIntoArray(inputMatrix, (0,1))
        h1 = indexIntoArray(inputMatrix, (0,0))
        h2 = indexIntoArray(inputMatrix, (2,1))
        h3 = indexIntoArray(inputMatrix, (2,0))
        h = [[h0, h1], [h2, h3]]
        
        inProcessArray = [[matrixDeterminant(a), matrixDeterminant(b), matrixDeterminant(c)],
                          [matrixDeterminant(d), matrixDeterminant(e), matrixDeterminant(f)],
                          [matrixDeterminant(g), matrixDeterminant(h), matrixDeterminant(i)]]
        
        return arrayMultiplyByScalar(inProcessArray, 1.0/det)
         

def matrixHorizontalConcatenate(leftMatrix, rightMatrix):
    """Concatenates rightMatrix to the right of leftMatrix.
    
    leftMatrix, rightMatrix -- list-formatted matrices.
    """
    try:
        leftRows, leftColumns = arraySize(leftMatrix)
        rightRows, rightColumns = arraySize(rightMatrix)
    except:
        raise errors.MatrixError("Cannot concatenate matrices. Input must be provided as a 2D array!")
        return False
    
    if leftRows != rightRows:
        raise errors.MatrixError("Cannot concatenate matrices. Input matrices must have same number of rows!")    
        return False
    else:
        return [list.__getitem__(leftMatrix, rowNumber) + list.__getitem__(rightMatrix,rowNumber) for rowNumber in range(leftRows)]
    

#--- BASIC GEOMETRY FUNCTIONS OPERATING ON TUPLES ---

class vector(object):
    """A (2D) vector object."""
    def __init__(self, startPoint, endPoint):
        """Initializes the vector object.

        For now, we are just initializing with a start and end point. But eventually it would be great to
        be able to initialize using start point and angle, or slope and intercept.

        Internally, vectors are stored as slope and intercept.
        """

        self.slope, self.intercept = self.slopeintercept(startPoint, endPoint)

    def __repr__(self):
        return "vector (a" + str(round(self.slope, 3)) + " b" + str(round(self.intercept, 3)) + ")"

    def __call__(self, independentValue):
        """Calling the vector returns its interpolated value at the provided independent value."""
        return self.interpolate(independentValue)

    def slopeintercept(self, startPoint = None, endPoint = None):
        """Returns the slope and intercept as a tuple.

        If startPoint and endPoint are supplied, the result will be based on that. Otherwise, it simply returns
        the stored slope and intercept of the vector object.
        """
        
        if startPoint: #actually calculate the slope and intercept.
            slope = (endPoint[1]-startPoint[1])/(endPoint[0]-startPoint[0])
            intercept = startPoint[1] - slope*startPoint[0]

            return slope, intercept

    def interpolate(self, independentValue):
        """Returns a point on the vector located at the provided independent value."""

        return self.slope * independentValue + self.intercept



