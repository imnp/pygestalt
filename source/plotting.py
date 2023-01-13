# pyGestalt Plotting Module

""" Provides the ability to plot simulation results, including performance and machine motion."""

from pygestalt import units, utilities, geometry, errors
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt


class dataset(list):
    def __init__(self, datapoint_list = [], units = ()):
        """Initializes the dataset.

        datapoints_list -- a list of datapoints in tuple format: [(x1, y1), (x2, y2), ...]
        units -- a tuple containing unit types that should be applied to the supplied datapoints
        """

        self.units = units

        #Determine dimension of the dataset data.
        if datapoint_list != []:
            self.dimension = len(datapoint_list[0])

            #check if unit dimensions match
            if units != ():
                if len(units) != self.dimension:
                    raise errors.PlottingError("Dimensionality of Units and Dataset don't Match!")

        #no data was provided
        else:
            if units != ():
                self.dimension = len(units)
            else:
                self.dimension = None

        super().__init__([self.convert_to_native_units(datapoint) for datapoint in datapoint_list])

        self.sort(key = self._sortFunction_)

    def __repr__(self):
        if self.units != ():
            unit_rep = " " + self._unitString_()
        else:
            unit_rep = ""

        return "dataset" + unit_rep + ": " + super().__repr__()

    def __call__(self, independentValue):
        """Returns the interpolated value of the dataset at the provided input value."""
        return self.interpolate(independentValue)

    def plot(self):
        x, y = tuple(zip(*self))

        figure, axes = plt.subplots()

        axes.plot(x, y)
        if self.units != ():
            plt.ylabel(units.getAbbreviation(self.units[1]))
            plt.xlabel(units.getAbbreviation(self.units[0]))

        plt.show()

    def interpolate(self, independentValue):
        """Returns the interpolated value of the dataset at the provided input value."""

        greaterValueIndex = self._findIndexOfFirstGreaterValue_(independentValue, 0)

        if greaterValueIndex == 0: #provided value is less than smallest datapoint
            segmentVector = geometry.vector(self[0], self[1])
            return segmentVector(independentValue) #extrapolate using the first two datapoints

        elif greaterValueIndex == -1: #provided value is greater than the largest datapoint
            segmentVector = geometry.vector(self[-2], self[-1])
            return segmentVector(independentValue)
        else:
            segmentVector = geometry.vector(self[greaterValueIndex-1], self[greaterValueIndex])
            return segmentVector(independentValue)


    def _findIndexOfFirstGreaterValue_(self, value, subindex):
        """Returns the index of the first datapoint whose value at subindex is greater than the input value.

        value -- the search value.
        subindex -- the index within each datapoint tuple to search.
        """

        for index, point in enumerate(self):
            if point[subindex] > value:
                return index

        return -1 #no greater value found


    def _sortFunction_(self, point):
        return point[0]

    def _unitString_(self):
        unitString = "("

        for unit in self.units:
            unitString += units.getAbbreviation(unit) + ", "

        return unitString[:-2]+")"


    def convert_to_native_units(self, datapoint):
        if self.units != ():
            variable_unit_tuples = zip(datapoint, self.units)
            return tuple([unit*variable for variable, unit in variable_unit_tuples])
        else:
            return datapoint





class plotter(object):
    def __init__(self, origin = "lower-left", width = "auto", height = "auto", resolution = 100, name = None):
        """Initializes the plotter.
        
        origin -- controls which quandrant is considered positive in both axes based on the position of the origin relative to this quadrant. 
                    Options are "lower-left", "lower-right", "upper-left", and "upper-right".
        width -- the width of the canvas, in real units. If not provided as a dFloat, will default to inches.
                 If "auto", the width will be drawn as needed to fully contain the artwork.
        height -- the height of the canvas, in real units. If not provided as a dFloat, will default to inches.
                  If the string "auto" is provided, the width will be drawn as needed to fully contain the artwork.
        resolution -- the rendering resolution of the image. If not provided as a dFloat, will default to pixels per inch.
        name -- the name of the plotter. Will be used in the title block of all drawn images.
        """
        self.setOrigin(origin) #will set the internal parameter self._coordinateTransformation_
        
        if width == "auto": 
            self.width = None
        else: 
            self.width = units.applyDefaultUnits(width, units.inch) #width defaults to inches
            
        if height == "auto":
            self.height = None
        else:
            self.height = units.applyDefaultUnits(height, units.inch) #height defaults to inches
        
        self.resolution = units.applyDefaultUnits(resolution, units.px/units.inch) #resolution defaults to pixels per inch
        
        self.name = name
        
    
    def setOrigin(self, origin):
        """Sets the internal coordinate transformation based on the position of the origin.
        
        origin -- the position of the origin relative to the purely positive quadrant. Options are "lower-left", "lower-right", "upper-left", 
                    and "upper-right".
        """
        # Note that PIL places the origin in the upper left by default.
        # self._coordinateTransform_ is stored as (inversionArray, shiftArray), which at rendering is used to perform the transformation into
        # PIL-space as (x,y)*inversionArray + (canvasWidth, canvasHeight)*shiftArray
        if origin == "lower-left": 
            self._coordinateTransform_ = (geometry.array([1,-1]), geometry.array([0,1]))
        elif origin == "lower-right": 
            self._coordinateTransform_ = (geometry.array([-1,-1]), geometry.array([1,1]))
        elif origin == "upper-left": 
            self._coordinateTransform_ = (geometry.array([1,1]), geometry.array([0,0]))
        elif origin == "upper-right": 
            self._coordinateTransform_ = (geometry.array([-1,1]), geometry.array([1,0]))
        else:
            utilities.notice(self, 'Invalid transformation "' + str(origin) + " provided to setOrigin()")
    
    
            
