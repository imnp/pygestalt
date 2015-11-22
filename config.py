# pyGestalt Config Module
"""The config module is used as a storage container to pass global state within a gestalt session."""



def setGlobalVariable(name, value):
    """Sets a global variable.
    
    name -- the name of the global variable to be set
    value -- the value to which the global variable should be set
    """
    globals().update({name:value})


def getGlobalVariable(name):
    """Returns the value of a requested global variable, or None if does not exist.
    
    name -- the name of the global variable whose value should be returned.
    """

    if name in globals():
        return globals()[name]
    else:
        return None


def syntheticModeOn():
    """Sets the global syntheticMode flag to True."""
    setGlobalVariable('syntheticModeFlag', True)

def syntheticModeOff():
    """Sets the global syntheticMode flag to False."""
    setGlobalVariable('syntheticModeFlag', False)

def syntheticMode():
    """Returns the current state of the syntheticMode flag."""
    return getGlobalVariable('syntheticModeFlag')

#Global flags
syntheticModeOff()