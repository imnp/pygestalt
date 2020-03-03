# MAGIC MILL CONTROLLER NODE
# 096-001b
# Re-written for pyGestalt 0.7
#
# March 1st, 2020
# Ilan E. Moyer
#
# Note: This virtual node is heavily based on 086-005b.

#---- IMPORTS ----
from pygestalt import nodes, core, packets, utilities, interfaces, config, units
from pygestalt.utilities import notice
import time
import math
import collections, Queue
import threading

#---- VIRTUAL NODE ----
class virtualNode(nodes.soloGestaltVirtualNode): #this is a solo Gestalt node
    
    def init(self):
        """Initializes the networked single-axis stepper virtual node."""
        
        # -- CURRENT SETTING PARAMETERS --
        
        # -> Variable Voltage Divider Parameters
        self.supplyVoltage = units.V(5.0)
        self.voltageDividerTopResistance = 10000.0 * units.V/units.A #in ohms. This is the resistance of the top leg of the motor reference voltage divider
        self.variablePotentiometerResistance = 5000.0 * units.V/units.A #in ohms. This is the max variable resistance of the bottom leg of the voltage divider.
        self.potentiometerSteps = 129.0 #full-range number of steps of the digital variable resistor
        self.maxReferenceVoltage = self.supplyVoltage * self.variablePotentiometerResistance / (self.variablePotentiometerResistance + self.voltageDividerTopResistance)
        
        # -> Stepper Driver Current Sensing 
        self.senseResistor = 0.1 * units.V/units.A #ohms
        self.stepperDriverCurrentGain = 1.0/ (8*self.senseResistor) #in amps/volt, per the A4988 datasheet, p9
        self.currentLimit = 2.0 * units.A #maximum rated current of the stepper driver
        
        # STEP GENERATION PARAMETERS
        self.clockFrequency = 18432000.0 #1/s, crystal clock frequency
        self.stepGenTimeBase = 1152.0 #number of system clock ticks per step interrupt
        self.stepGenPeriod = float(self.stepGenTimeBase) / self.clockFrequency #the time per step gen interrupts, in seconds
        
        # AXES
        self.size = 3 #number of axes
        
        # MOTION BUFFER AND KEYS
        self.motionBufferSize = 48
        self.motionSegmentBuffer = self.motionSegmentManager(motionKeyMax = 255, bufferSize = self.motionBufferSize)
        
        
        # SYNTHETIC PARAMETERS
        self.syntheticMotorEnableFlag = 0 #tracks whether the motor is enabled when in synthetic mode.
        self.syntheticCurrentKey = 0
        self.syntheticTimeRemaining = 0
        self.syntheticReadPosition = 0
        self.syntheticWritePosition = 0
        self.syntheticStepperPositions = [0 for i in range(self.size)]
        
        # SYNTHETIC BUFFER
        self.syntheticMotionBuffer = collections.deque()
        
        if(config.syntheticMode()): #running in synthetic mode
            self.syntheticStepGenerator = threading.Thread(target = self.syntheticStepGeneratorThread, kwargs = {'syntheticMotionBuffer':self.syntheticMotionBuffer,
                                                                                      'virtualNode': self})
            self.syntheticStepGenerator.daemon = True                                 
            self.syntheticStepGenerator.start() 

        
    def initPackets(self):
        """Initializes all packet definitions"""
        
        self.setCurrentReferenceVoltageRequestPacket = packets.template('setCurrentReferenceVoltageRequest',
                                                                          packets.unsignedInt('axis', 1), #axis is 0:2
                                                                          packets.unsignedInt('value', 1)) #potentiometer setting
        
        self.setCurrentReferenceVoltageResponsePacket = packets.template('setCurrentReferenceVoltageResponse',
                                                                         packets.unsignedInt('status',1)) #0: success, 32 or 48: NACK error, 56: arbitration error
        
        self.enableDriverRequestPacket = packets.template('enableDriverRequest',
                                                    packets.unsignedInt('enable', 1))
        
        self.stepRequestPacket = packets.template('stepRequest',
                                                  packets.fixedPoint('stepper1_target', 22, 2), #24-bit total, 2 fractional step bits (1/4 steps).
                                                  packets.unsignedInt('segmentTime', 3), #24-bit unsigned. The move time in units of 62.5us.
                                                  packets.unsignedInt('segmentKey', 1), #a rolling key counter that helps to identify the active segment on the node 
                                                  packets.unsignedInt('absoluteMove', 1), #0: relative move, 1: absolute move
                                                  packets.unsignedInt('sync', 1)) #synchronized move if non-zero
        
        self.positionResponsePacket = packets.template('positionResponse',
                                                  packets.fixedPoint('stepper1_absolutePosition', 22, 2)) #24-bit total, 2 fractional step bits (1/4 steps).

        
        self.stepStatusResponsePacket = packets.template('stepStatusResponse',
                                                 packets.unsignedInt('statusCode', 1), #1 if a move is queued successfully, 0 if buffer is full.
                                                 packets.unsignedInt('currentKey', 1), #key of current motion segment
                                                 packets.unsignedInt('timeRemaining', 3), #segment time remaining, in units of 62.5us
                                                 packets.unsignedInt('readPosition', 1), #position of the read head
                                                 packets.unsignedInt('writePosition', 1)) #position of the write head
        

    
    def initPorts(self):
        """Binds functions and packets to ports"""
        self.bindPort(port = 11, outboundFunction = self.setCurrentReferenceVoltageRequest, outboundTemplate = self.setCurrentReferenceVoltageRequestPacket, inboundTemplate = self.setCurrentReferenceVoltageResponsePacket)
        self.bindPort(port = 12, outboundFunction = self.enableDriverRequest, outboundTemplate = self.enableDriverRequestPacket)
        self.bindPort(port = 13, outboundFunction = self.stepRequest, outboundTemplate = self.stepRequestPacket, inboundTemplate = self.stepStatusResponsePacket)
        self.bindPort(port = 14, outboundFunction = self.getPositionRequest, inboundTemplate = self.positionResponsePacket)
        self.bindPort(port = 15, outboundFunction = self.stepStatusRequest, inboundTemplate = self.stepStatusResponsePacket)

    
    #-- PUBLIC USER FUNCTIONS --
    def setMotorCurrent(self, a = None, b = None, c = None):
        """Sets the stepper motor drive current for each of the three axes.
        
        a -- the current setting for motor "a", in amps
        b -- the current setting for motor "b", in amps
        c -- the current setting for motor "c", in amps
        
        Returns True if successful in setting all motor currents, or False if not.
        """
        
        for axis, motorCurrent in enumerate([a, b, c]):
            if (motorCurrent < self.currentLimit) and (motorCurrent >=0): #check that within bounds
                requestedReferenceVoltage = motorCurrent / self.stepperDriverCurrentGain #gain is in amps/volt
                actualReferenceVoltage = self.setCurrentReferenceVoltageRequest(axis, requestedReferenceVoltage)
                if actualReferenceVoltage != None:
                    actualCurrent = self.stepperDriverCurrentGain * actualReferenceVoltage
                    notice(self, ["A", "B", "C"][axis] + " axis motor current set to " + str(round(actualCurrent, 1)) + "amps.")
                else:
                    notice(self, "Unable to set " + ["A", "B", "C"][axis] + "motor current.")
                    return False
            else:
                if motorCurrent != None: # check that motor current was provided
                    notice(self, "Motor current must be between 0.0 and " + str(self.currentLimit) + "amps.")
                    return False
        return True

    #-- SEGMENT MANAGER --
    class motionSegmentManager(object):
        """Mirrors the current motionSegment buffer, to facilitate pausing and recovery."""
        def __init__(self, motionKeyMax = 255, bufferSize = 48):
            """Initializes the motion segment memory manager.
            
            motionKeyMax -- the maximum value of the motion key before it rolls over
            bufferSize -- the size of the motion segment buffer on the physical node
            """
            self.motionKey = 0 #reset the motion key
            self.motionKeyMax = motionKeyMax
            self.maxBufferSize = bufferSize #the max
             # create a double-ended queue to store motion segments. This is particularly useful for tasks like pausing,
             # or identifying the total motion time remaining in the buffer. We can limit the buffer to maxBufferSize
            self.segmentBuffer = collections.deque(maxlen = self.maxBufferSize)
            
        
        def newKey(self):
            """Pulls and returns a new key for tracking motion segments in the node's buffer"""
            self.motionKey += 1 #increment the motion key
            if self.motionKey > self.motionKeyMax: #roll over if exceeds max
                self.motionKey = 0
            return self.motionKey
        
        def addSegmentToBuffer(self, stepActionObject):
            """Adds an step request actionObject to the buffer.
            
            stepActionObject -- a stepRequest actionObject
            """
            self.segmentBuffer.appendleft(stepActionObject) #note that once the buffer size is exceeded, objects will drop off the other end
            
    
    #-- UTILITY FUNCTIONS --
    
    
    #-- SERVICE ROUTINES --
    class setCurrentReferenceVoltageRequest(core.actionObject):
        def init(self, axis, voltage):
            """Sets the voltage on the driver current reference pin for the specified stepper driver.
            
            axis -- the index of the axis, specified as 0, 1, or 2, corresponding respectively to the A, B, or C stepper drivers
            voltage -- a voltage value, provided as a float or units.dFloat
                
            Note that because of the quantization of the voltages by the discrete digital potentiometer, the actual setting may differ from the request.

            Returns the actual voltage setting if successful or otherwise None.
            """
            
            potentiometerValue = int(self.virtualNode.potentiometerSteps*float(voltage)/self.virtualNode.maxReferenceVoltage) #the potentiometer value.
            if potentiometerValue >= self.virtualNode.potentiometerSteps: #clamp the max value at the top of the potentiometer range
                potentiometerValue = self.virtualNode.potentiometerSteps
                notice(self.virtualNode, 'Requested reference voltage exceeded maximum. Set Vref to ' + str(self.virtualNode.maxReferenceVoltage))
            
            actualVoltage = (potentiometerValue * self.virtualNode.maxReferenceVoltage) / self.virtualNode.potentiometerSteps
            
            self.setPacket(axis = axis, value = voltage)
            
            if self.transmitUntilResponse():
                status = self.getPacket()['status'] #the response status
                if status == 0: #load was successful, so return the actual voltage that was set
                    return actualVoltage
                elif status == 32:
                    notice(self.virtualNode, 'received a NACK when sending address to the digital potentiometer')
                    return None
                elif status == 48:
                    notice(self.virtualNode, 'received a NACk when sending data to the digital potentiometer')
                    return None
                elif responseValue == 56:
                    notice(self.virtualNode, 'arbitration lost while communicating with the digital potentiometer')
                    return None
                else:
                    notice(self.virtualNode, 'unknown response value received while communicating with digital potentiometer: ' + str(status))
                    return None               
            else:
                notice(self.virtualNode, 'Received no response to set current reference voltage request.')
                return None
            
        def synthetic(self, axis, value):
            return {'status':0}
        
        
    class enableDriverRequest(core.actionObject):
        def init(self, enable = True):
            """Enables or disables the motor driver, causing the stepper coils to become energized or lose power.
            
            enable -- if True, enables the driver. If false, disables the driver.
            
            Returns True if successful, or False otherwise.
            """
            self.setPacket(enable = {True:1, False:0}[enable]) #1 if enable, 0 if disable
            
            if self.transmitUntilResponse():
                if enable:
                    notice(self.virtualNode, 'Stepper Motor '+ {True:'Enabled',False:'Disabled'}[enable] + '.')
                return True
            else:
                notice(self.virtualNode, 'Failed to '+ {True:'Enable',False:'Disable'}[enable] + ' Stepper Motor!')
                return False
    
        def synthetic(self):
            self.virtualNode.syntheticMotorEnableFlag = {True:1, False:0}[enable]
            return {}   
    
    class stepRequest(core.actionObject):
        def init(self, target, segmentTime, absoluteMove = False):
            segmentKey = self.virtualNode.motionSegmentBuffer.newKey() #pull a new segment key
            self.segmentTime = segmentTime
            
            #set the outgoing packet, based on the information avaliable now.
            self.setPacket(stepper1_target = target, segmentTime = self.segmentTime, segmentKey = segmentKey, absoluteMove = {False:0, True:1}[absoluteMove], sync = {False:0, True:1}[self.isSync()])
            
            if not self.isSync(): #not a synchronized move, so make it happen now.
                return self.sendMotionSegment()
            else: #synchronized move.
                pass #we're going to do everything in separate methods at the right time.
        
        def onSyncPush(self):
            """Push synchronizing parameters to the sync token."""
            self.syncToken.push(segmentTime = self.segmentTime) #push the segment move time
        
        def onSyncPull(self):
            """Pull synchronizing parameters from the sync token."""
            maxSegmentTime = self.syncToken.pullMaxValue('segmentTime')
            self.setPacket(segmentTime = maxSegmentTime) #make sure that all synchronized nodes are using the same segment time
        
        def onChannelAccess(self):
            """Runs when actionObject receives access to the communication channel."""
            if self.isSync(): #don't want to send twice if not a synchronized move.
                self.sendMotionSegment()
        
        def sendMotionSegment(self):
            """Sends a motion segment to the node."""
            while True: #make sure the motion segment is loaded into the buffer
                if self.transmitUntilResponse(releaseChannelOnTransmit = False): #may need to transmit multiple times if buffer is full, so don't release channel automatically
                    response = self.getPacket()
                    if response['statusCode']: #segment was loaded
                        self.releaseChannel() #Done; release the communications channel
                        break
                    else: #buffer was full
                        timeUntilSlotAvailable = self.virtualNode.stepGenPeriod * response['timeRemaining']
                        notice(self, "MOVE " + str(segmentKey) + ": BUFFER FULL... WAITING " + str(timeUntilSlotAvailable) + " s")
                        time.sleep(timeUntilSlotAvailable)
                else:
                    notice(self.virtualNode, 'Unable to send motion segment!')
                    return False            
                 
        def synthetic(self, stepper1_target, segmentTime, segmentKey, absoluteMove, sync):
            if(len(self.virtualNode.syntheticMotionBuffer)<= self.virtualNode.motionBufferSize): #space available in buffer
                self.virtualNode.syntheticMotionBuffer.appendleft({'stepper1_target':stepper1_target, 'segmentTime':segmentTime, 'segmentKey': segmentKey,
                                                                   'absoluteMove':absoluteMove, 'sync':sync})
                self.virtualNode.syntheticWritePosition += 1
                if(self.virtualNode.syntheticWritePosition == self.virtualNode.motionBufferSize):
                    self.virtualNode.syntheticWritePosition = 0
                return {'statusCode':1, 'currentKey': self.virtualNode.syntheticCurrentKey, 'timeRemaining': self.virtualNode.syntheticTimeRemaining, 
                        'readPosition': self.virtualNode.syntheticReadPosition, 'writePosition': self.virtualNode.syntheticWritePosition}
            else:
                return {'statusCode':0, 'currentKey': self.virtualNode.syntheticCurrentKey, 'timeRemaining': self.virtualNode.syntheticTimeRemaining, 
                        'readPosition': self.virtualNode.syntheticReadPosition, 'writePosition': self.virtualNode.syntheticWritePosition}            

    class getPositionRequest(core.actionObject):
        def init(self):
            if self.transmitUntilResponse():
                return self.getPacket()['stepper1_absolutePosition']
            else:
                notice(self.virtualNode, 'Unable to get absolute position!')
                return False  

        def synthetic(self):
            print self.virtualNode.syntheticStepperPositions[0]
            return {'stepper1_absolutePosition':self.virtualNode.syntheticStepperPositions[0]}
                       
            
    class stepStatusRequest(core.actionObject):
        def init(self):
            """Returns the current motion status of the node.
            
            Returns a dictionary containing the following keys:
                statusCode -- will always read 1 to a spinStatusRequest. In the context of the response to a spin request, indicates whether the move was queued successfully.
                currentKey -- Each motion segment is assigned a sequential ID to confirm nothing has been lost. This will return the key of the motion segment currently
                              under the buffer read head.
                timeRemaining -- The time remaining in the current move, in step generator ticks (currently 62.5us).
                readPosition -- The current position of the read head, which is the buffer location that was last read.
                writePosition -- The current position of the write head, which is the buffer location that was last written.
            """
            if self.transmitUntilResponse():
                return self.getPacket()
            else:
                notice(self.virtualNode, 'Unable to get spin status!')
                return False
        
        def synthetic(self):
            return {'statusCode':1, 'currentKey': self.virtualNode.syntheticCurrentKey, 'timeRemaining': self.virtualNode.syntheticTimeRemaining, 
                    'readPosition': self.virtualNode.syntheticReadPosition, 'writePosition': self.virtualNode.syntheticWritePosition}

    def syntheticSync(self):
        """Overrides the base class method, and is run in synthetic mode whenever a synchronization request is made."""
        for motionSegment in reversed(self.syntheticMotionBuffer):
            if motionSegment['sync'] ==1:
                motionSegment['sync'] = 0
                return
        notice(self, "SYNTHETIC SYNC: Received Extra Sync Command!")

    # ----- SYNTHETIC MOTION THREAD -----
    def syntheticStepGeneratorThread(self, syntheticMotionBuffer, virtualNode):
        while True:
            if(len(syntheticMotionBuffer)>0):
                if(syntheticMotionBuffer[-1]['sync'] == 0): #OK to load move
                    currentMove = syntheticMotionBuffer.pop()
                    virtualNode.syntheticCurrentKey = currentMove['segmentKey']
                    virtualNode.syntheticTimeRemaining = currentMove['segmentTime']
                    virtualNode.syntheticReadPosition += 1
                    if(virtualNode.syntheticReadPosition == virtualNode.motionBufferSize):
                        virtualNode.syntheticReadPosition = 0
                    time.sleep(virtualNode.syntheticTimeRemaining*virtualNode.stepGenPeriod)
                    if(currentMove['absoluteMove']):
                        relativeMotion = currentMove['stepper1_target'] - virtualNode.syntheticStepperPositions[0]
                    else:
                        relativeMotion = currentMove['stepper1_target']
                    virtualNode.syntheticStepperPositions[0] += relativeMotion
            time.sleep(0.001)

if __name__ == "__main__":
    config.syntheticModeOn()
    stepperNode = virtualNode()
    stepperNode.setMotorCurrent(0.8, 0.2)
