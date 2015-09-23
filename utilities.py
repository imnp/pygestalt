#   pyGestalt Utilities Module

"""Provides a host of common utility functions used across the pyGestalt framework."""


#---- IMPORTS ----
import math
import ast
import datetime

def unsignedIntegerToBytes(integer, numbytes):
    """Converts an unsigned integer into a sequence of bytes, LSB first."""
    bytes = range(numbytes)
    for i in bytes:
        bytes[i] = integer%256
        integer -= integer%256
        integer = integer//256
        
    if integer>0: raise IndexError('Overflow in conversion between uint and byte list.')
    else: return bytes