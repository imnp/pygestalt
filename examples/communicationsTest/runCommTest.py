""" Runs a communication test with a target node."""

# ---- IMPORTS ----
from pygestalt import nodes, config
import time

# ---- SYNTHETIC MODE ----
# config.syntheticModeOn() #Un-comment this line to run in synthetic mode (i.e. test mode)
# config.verboseDebugOn()
# config.setDebugChannels()

# ---- DEFINE TEST NODE ----
# testNode = nodes.arduinoGestaltNode(name = "Comm. Test Node", filename = "arduinoNode_commTest.py") #filename must be provided for synthetic mode
testNode = nodes.networkedGestaltNode(name = "Comm. Test Node", filename = "gestaltNode_commTest.py") #filename must be provided for synthetic mode

# ---- TEST FUNCTIONS ----
def exchange(outboundPayloadLength, inboundPayloadLength, numExchanges = 1, verbose = False):
    """Executes a series of bi-directional packet exchanges with the test node.
    
    outboundPayloadLength -- the length (in bytes) of the outbound payload
    inboundPayloadLength -- the length (in bytes) of the inbound payload
    numExchanges -- the number of back-and-forth exchanges with the physical node
    verbose -- if True, will print current test to the terminal
    
    Returns the average round-trip time (in seconds) required for the requested exchanges.
    """
    startTime = time.time()
    if verbose:
        print "Running " + str(numExchanges) + " exchanges with " + str(outboundPayloadLength) + " outbound and " + str(inboundPayloadLength) + " inbound bytes."
    for exchangeIndex in range(numExchanges):
        testNode.exchangeTestPacket(outboundPayloadLength, inboundPayloadLength)
    
    elapsedTime = time.time() - startTime
    averageRoundTripTime = elapsedTime / float(numExchanges)
    if verbose:
        print "  -> " + str(round(1.0/averageRoundTripTime, 1)) + " exchanges per second."
    return averageRoundTripTime

def symmetricPayloadSizeSweep(startSize, endSize, numExchanges, verbose = False):
    """Tests the packet exchange rate with a physical node across a range of payload sizes.
    
    startSize -- the number of payload bytes in the outbound and inbound packet at the start of the sweep
    endSize -- the number of payload bytes in the outbound and inbound packet at the end of the sweep
    numExchanges -- the number of test packet exchanges to conduct for each payload size.
    verbose -- if True, provides progress information
    
    returns [(payloadSize, exchangeRate), ...] for each payload size in the sweep.
        payloadSize -- the number of payload bytes in the outbound and inbound packets
        exchangeRate -- the number of round-trip exchanges that were executed per second.
    """
    return [(payloadSize, round(1.0 / exchange(payloadSize, payloadSize, numExchanges, verbose),1)) for payloadSize in range(startSize, endSize + 1)]
    
def printResult(sweepResult):
    print " "
    print "PAYLOAD SWEEP RESULTS:"
    for payloadSize, exchangeRate in sweepResult:
        print "  " + str(payloadSize) + " PAYLOAD BYTES: " + str(exchangeRate) + " ROUND-TRIP PACKETS PER SEC."
    
# ---- LOAD NEW FIRMWARE ----
testNode.loadProgram('firmware/gestaltNode_commTest/gestaltNode_commTest.hex')

# ---- RUN TEST ----
# printResult(symmetricPayloadSizeSweep(0,3, 100, verbose = True))
