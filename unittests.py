#   pyGestalt Unit Testing Module

"""A set of unit tests to ensure that the library is functioning properly."""

# ----IMPORTS----
import unittest
import pygestalt.packets

#----Utilities Module----
# -> function inputs are within bounds
# -> all necessary function inputs are provided
# -> function inputs are the correct type

#----Packets Module----
# -> token inputs are within bounds
# -> all necessary token inputs are provided
# -> token inputs are the correct type
# -> packets are composed correctly
# -> each token encodes and decodes correctly over a range of values and edge cases
# -> end-to-end tests of packet configurations including weird ones like checksum in the middle, etc.
# -> in fixed-point token make sure that number of specified bits plus the sign bit adds up to an integer # of bytes, to prevent user error.
# -> no duplicate token names, even across embedded templates

