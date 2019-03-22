# pyGestalt Config Module
"""The config module is used as a storage container to pass global state within a pyGestalt session."""



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

#global synthetic mode
def syntheticModeOn():
    """Sets the global syntheticMode flag to True."""
    setGlobalVariable('syntheticModeFlag', True)

def syntheticModeOff():
    """Sets the global syntheticMode flag to False."""
    setGlobalVariable('syntheticModeFlag', False)

def syntheticMode():
    """Returns the current state of the syntheticMode flag.
    
    If global synthetic mode is enabled, all nodes will issue synthetic responses to actionObject requests.
    """
    return getGlobalVariable('syntheticModeFlag')

#automatically download virtual nodes
def automaticNodeDownload():
    """Returns the current state of the automaticNodeDownload flag.
    
    If automatic node downloads are enabled, pyGestalt will first attempt to download a virtual node from
    the web address provided by the physical node upon association. If this is unsuccessful, pyGestalt will
    then attempt to find the virtual node file in the local directory.
    """
    return getGlobalVariable('automaticNodeDownload')

def automaticNodeDownloadOn():
    """Sets the global automaticNodeDownload flag to True."""
    setGlobalVariable('automaticNodeDownload', True)
    
def automaticNodeDownloadOff():
    """Sets the global automaticNodeDownload flag to False."""
    setGlobalVariable('automaticNodeDownload', True)




#global verbose debug
def verboseDebugOn():
    """Sets the global verboseDebug flag to True."""
    setGlobalVariable('verboseDebugFlag', True)

def verboseDebugOff():
    """Sets the global verboseDebug flag to False."""
    setGlobalVariable('verboseDebugFlag', False)

def verboseDebug():
    """Returns the current state of the verboseDebug flag.
    
    If global verbose debug is enabled, any calls to utilities.debugNotice will result in a notification output.
    """
    return getGlobalVariable('verboseDebugFlag')

def setDebugChannels(*channelNames):
    """Enables selected debug channel names.
    
    channelNames -- any number of arguments, each of which is a string corresponding to the name of a debug channel to enable.
                    If no arguments are provided, all channels will be enabled.
    
    Only enabled channels will report debug messages.
    """
    setGlobalVariable('verboseDebugChannels', channelNames)
    
def debugChannelEnabled(debugChannel):
    """Returns True if a debug channel is enabled"""
    debugChannels = getGlobalVariable('verboseDebugChannels')
    return (debugChannels == () or debugChannel in debugChannels)
    

#Global flags
syntheticModeOff()
automaticNodeDownloadOff()
# verboseDebugOn()
setDebugChannels('units')