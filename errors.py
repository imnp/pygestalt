#   pyGestalt Errors Module

"""Defines custom exceptions that are used across the pyGestalt framework."""

class Error(Exception):
    pass

class CompositionError(Error):
    pass

class UnitError(Error):
    pass

class UnitConversionError(Error):
    pass

class ArrayError(Error):
    pass