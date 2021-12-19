# pyGestalt Plotting Module

""" Provides the ability to plot the motion of machines in simulation.

This module is largely a pyGestalt-friendly wrapper for a small subset of the Pillow library.
"""

from pygestalt import units, utilities, geometry
from PIL import Image, ImageDraw, ImageFont

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
    
    
            
