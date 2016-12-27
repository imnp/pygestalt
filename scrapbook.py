#just a scrapbook of code that might want to reference even if it's been taken out.


#raising errors
if templateName: errorMessage = str(self.keyName) + " not found in template " + templateName + "."
else: errorMessage = str(self.keyName) + " not found in template."
raise KeyError(errorMessage)

def _getItem_(self, positionTuple, subArray = None):
    """Internal recursive method for indexing into a multi-dimensional array.
    
    positionTuple -- this is provided by the Python interpreter when the array is indexed
    subArray -- this is only used internally for the recursive algorithm
    
    Note that the intended pattern is that this method gets called by __getitem__. It is broken out
    because __getitem__ might be overridden by child classes such as geometry.matrix to enforce
    a particular dimensionality of the result.
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
            return array(subArray)
        else:
            slicedArrayList = [[self._getItem_(positionRemainder, arraySlice)] for arraySlice in subArray]
            return array(slicedArrayList)
    else: #asking for an indexed value:
        try:
            indexedValue = subArray[positionIndex]
        except:
            raise errors.ArrayError("Index Error - index out of bounds of array")
            return False
        
        if isinstance(indexedValue, list): #need to index deeper into the array
            if positionRemainder == (): #no index provided!
                raise errors.ArrayError("Index Error - array is larger than number of indices provided")
                return False
            else:
                return self._getItem_(positionRemainder, indexedValue)
        else: #end of array
            if positionRemainder == (): #no extra indices requested, good!
                return indexedValue #finally return the value
            else:
                raise errors.ArrayError("Index Error - array is smaller than number of indices provided")
                return False
            
            
#check if array has more dimensions than indices provide.
inputArraySize = arraySize(inputArray)
if len(inputArraySize) > len(indexTuple): #Ignore as many initial dimensions with a size of 1 as possible.
    possibleDimensionsToIgnore = inputArraySize[:(len(inputArraySize)-len(indexTuple))]
    print "PossibleDimensionsToIgnore" + str(possibleDimensionsToIgnore)
    dimensionsToIgnore = ()
    for dimension in possibleDimensionsToIgnore:
        if dimension == 1:
            dimensionsToIgnore += (0,)
        else:
            break
        
def __getitem__(self, positionTuple):
    """Returns an individual item or a slice in the matrix.
    
    positionTuple -- this is provided by the Python interpreter when the array is indexed
    
    This method over-rides the __getitem__ method of the array type, so that it can return a matrix rather than an array.
    To index into a specific cell of a matrix, simply index as myMatrix[1,2] to retrieve item in row 1, column 2.
    To index an entire subarray, index as myArray[1,:] to retrieve all of row 1.
    If the number of indices in positionTuple is less than the dimensionality of the array,
        and if no slices are used, then indexing starts at the first dimension whose size is greater than 1.
        This is to support compatibility between various formats of arrays, i.e. a 1D array and a 2D 1xN array.
    """
    getItemResult = self._getItem_(positionTuple)
    
    if type(getItemResult) == array:
        return matrix(getItemResult)
    else:
        return getItemResult
    indexTuple = dimensionsToIgnore