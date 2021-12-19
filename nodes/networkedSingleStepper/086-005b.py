# SINGLE AXIS NETWORKED STEPPER NODE
# 086-005b
# Re-written for pyGestalt 0.7
#
# April 13th, 2019
# Ilan E. Moyer

#---- IMPORTS ----
from pygestalt import nodes, core, packets, utilities, interfaces, config, units
from pygestalt.utilities import notice
import time
import math
import collections, Queue
import threading

#---- VIRTUAL NODE ----
class virtualNode(nodes.networkedGestaltVirtualNode): #this is a networked Gestalt node
    
    def init(self):
        """Initializes the networked single-axis stepper virtual node."""
        
        # CURRENT LIMIT PARAMETERS
        self.ADCReferenceVoltage = units.V(5.0)
        self.ADCFullScale = 1024 #integer number corresponding to the full-scale ADC reference voltage.
        self.senseResistor = 0.1 * units.V/units.A #ohms
        self.stepperDriverCurrentGain = 1.0/ (8*self.senseResistor) #in amps/volt, per the A4988 datasheet, p9
        
        # STEP GENERATION PARAMETERS
        self.clockFrequency = 18432000.0 #1/s, crystal clock frequency
        self.stepGenTimeBase = 1152.0 #number of system clock ticks per step interrupt
        self.stepGenPeriod = float(self.stepGenTimeBase) / self.clockFrequency #the time per step gen interrupts, in seconds
        self.stepGenUnits = units.unit("tks", "ticks", units.s, 1.0/self.stepGenPeriod) #used for converting between step generator units and seconds
        
        # AXES
        self.size = 1 #number of axes
        
        # MOTION BUFFER AND KEYS
        self.motionBufferSize = 48
        self.motionSegmentBuffer = self.motionSegmentManager(motionKeyMax = 255, bufferSize = self.motionBufferSize)
        
        
        # SYNTHETIC PARAMETERS
        self.syntheticMotorCurrentReferenceVoltage = 0 #this is set to match the current request inside setMotorCurrent()
        self.syntheticMotorEnableFlag = 0 #tracks whether the motor is enabled when in synthetic mode.
        self.syntheticCurrentKey = 0
        self.syntheticTicksRemaining = 0
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
        
        self.readCurrentReferenceVoltageResponsePacket = packets.template('readCurrentReferenceVoltageResponse',
                                                                          packets.unsignedInt('vrefValue',2)) #the raw ADC value of the driver voltage reference
        
        self.enableDriverRequestPacket = packets.template('enableDriverRequest',
                                                    packets.unsignedInt('enable', 1))
        
        self.stepRequestPacket = packets.template('stepRequest',
                                                  packets.fixedPoint('stepper1_target', 22, 2), #24-bit total, 2 fractional step bits (1/4 steps).
                                                  packets.unsignedInt('segmentTicks', 3), #24-bit unsigned. The move time in units of 62.5us.
                                                  packets.unsignedInt('segmentKey', 1), #a rolling key counter that helps to identify the active segment on the node 
                                                  packets.unsignedInt('absoluteMove', 1), #0: relative move, 1: absolute move
                                                  packets.unsignedInt('sync', 1)) #synchronized move if non-zero
        
        self.positionResponsePacket = packets.template('positionResponse',
                                                  packets.fixedPoint('stepper1_absolutePosition', 22, 2)) #24-bit total, 2 fractional step bits (1/4 steps).

        
        self.stepStatusResponsePacket = packets.template('stepStatusResponse',
                                                 packets.unsignedInt('statusCode', 1), #1 if a move is queued successfully, 0 if buffer is full.
                                                 packets.unsignedInt('currentKey', 1), #key of current motion segment
                                                 packets.unsignedInt('ticksRemaining', 3), #segment time remaining, in units of 62.5us
                                                 packets.unsignedInt('readPosition', 1), #position of the read head
                                                 packets.unsignedInt('writePosition', 1)) #position of the write head
        

    
    def initPorts(self):
        """Binds functions and packets to ports"""
        self.bindPort(port = 11, outboundFunction = self.readCurrentReferenceVoltageRequest, inboundTemplate = self.readCurrentReferenceVoltageResponsePacket)
        self.bindPort(port = 12, outboundFunction = self.enableDriverRequest, outboundTemplate = self.enableDriverRequestPacket)
        self.bindPort(port = 13, outboundFunction = self.stepRequest, outboundTemplate = self.stepRequestPacket, inboundTemplate = self.stepStatusResponsePacket)
        self.bindPort(port = 14, outboundFunction = self.getPositionRequest, inboundTemplate = self.positionResponsePacket)
        self.bindPort(port = 15, outboundFunction = self.stepStatusRequest, inboundTemplate = self.stepStatusResponsePacket)

    
    #-- PUBLIC USER FUNCTIONS --
    def setMotorCurrent(self, targetMotorCurrent, currentTolerance = 0.05):
        """Instructs user on setting the motor current by turning the vref knob.
        
        targetMotorCurrent -- the target motor current in amps
        currentTolerance -- the deviation from target current that is allowed for the function to exit.
                            Note that the tolerance for setting the current is tighter than for accepting the setting initially.
                            This hysteresis is to help setting closer to nominal while permitting some drift.
        
        This function will continue to run until the motor current is within tolerance of the target.
        """
        
        if not utilities.fuzzyEquals(self.readMotorCurrent(), targetMotorCurrent, currentTolerance):
            #check if motor current is within tolerance before beginning UI routine.
            while True:
                actualMotorCurrent = self.readMotorCurrent() #get the actual motor current
                if not utilities.fuzzyEquals(actualMotorCurrent, targetMotorCurrent, currentTolerance*0.75):
                    if actualMotorCurrent>targetMotorCurrent:
                        notice(self, 'Motor Current: '+ str(round(actualMotorCurrent, 2)) + 'A / ' + 
                                        str(round(targetMotorCurrent,2)) + 'A. Turn trimmer CW.')
                    else:
                        notice(self, 'Motor Current: '+ str(round(actualMotorCurrent, 2)) + 'A / ' + 
                                        str(round(targetMotorCurrent,2)) + 'A. Turn trimmer CCW.')
                else:
                    notice(self, "Motor Current Set To: "+ str(round(actualMotorCurrent, 2)) + 'A')
                    break
                
                if config.syntheticMode():
                    self.syntheticMotorCurrentReferenceVoltage = (float(targetMotorCurrent) /self.stepperDriverCurrentGain)
                
                time.sleep(0.5)

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
    def readMotorCurrent(self):
        """Returns the peak motor current per phase, based on reading the vref intput to the stepper driver.
        
        Returns
            motorCurrent -- the peak-motor-current-per-phase setting of the stepper driver.
        """
        vref = self.readCurrentReferenceVoltageRequest()
        return self.stepperDriverCurrentGain * vref
    
    
    #-- SERVICE ROUTINES --
    class readCurrentReferenceVoltageRequest(core.actionObject):
        def init(self):
            """Returns the voltage on the stepper driver current reference pin."""
            if self.transmitUntilResponse():
                vrefADCReading = self.getPacket()['vrefValue'] #the raw ADC reading
                return (vrefADCReading / float(self.virtualNode.ADCFullScale))*self.virtualNode.ADCReferenceVoltage
            else:
                notice(self.virtualNode, 'Received no response to read reference voltage request.')
                return False
            
        def synthetic(self):
            voltageRatio = self.virtualNode.syntheticMotorCurrentReferenceVoltage/self.virtualNode.ADCReferenceVoltage
            vrefValue = int(voltageRatio*self.virtualNode.ADCFullScale)
            return {'vrefValue':vrefValue}
        
        
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
            """Steps to a relative or absolute target in a given amount of time.
            
            target -- the target number of steps (if relative), or the target position (if absolute)
            segmentTime -- the requested duration of the motion segment, in seconds.
            absoluteMove -- if True, the target is an absolute position. If False, the target is a relative number of steps (including a sign).
            """
            
            segmentKey = self.virtualNode.motionSegmentBuffer.newKey() #pull a new segment key
            
            self.segmentTicks = self.virtualNode.stepGenUnits(units.s(segmentTime)) #the actual move time, in ticks
            self.segmentTime = units.s(self.segmentTicks) #the actual move time, in seconds
            
            #set the outgoing packet, based on the information avaliable now.
            self.setPacket(stepper1_target = target, segmentTicks = self.segmentTicks, 
                           segmentKey = segmentKey, absoluteMove = {False:0, True:1}[absoluteMove], sync = {False:0, True:1}[self.isSync()])
            
            if not self.isSync(): #not a synchronized move, so make it happen now.
                return self.sendMotionSegment()
            else: #synchronized move.
                pass #we're going to do everything in separate methods at the right time.
        
        def onSyncPush(self):
            """Push synchronizing parameters to the sync token."""
            self.syncToken.push(segmentTime = self.segmentTime) # push the ACTUAL segment move time. Note that this will be a multiple of the step gen time,
                                                                # because it is calculated as such in init(). This is important for detecting incompatible
                                                                # step gen periods between nodes. 
        
        def onSyncPull(self):
            """Pull synchronizing parameters from the sync token."""
            maxSegmentTime = self.syncToken.pullMaxValue('segmentTime')
            segmentTicks = self.virtualNode.stepGenUnits(maxSegmentTime)
            actualSegmentTime = units.s(segmentTicks)
            if actualSegmentTime != maxSegmentTime:
                notice(self.virtualNode, "WARNING: INCOMPATIBLE STEP GENERATOR TIME BASES DETECTED DURING SYNCHRONIZATION.")
            self.setPacket(segmentTicks = segmentTicks) #make sure that all synchronized nodes are using the same segment time
        
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
                        timeUntilSlotAvailable = units.s(self.virtualNode.stepGenUnits(response['ticksRemaining']))
                        notice(self, "MOVE " + str(response['currentKey']) + ": BUFFER FULL... WAITING " + str(timeUntilSlotAvailable))
                        time.sleep(timeUntilSlotAvailable)
                else:
                    notice(self.virtualNode, 'Unable to send motion segment!')
                    return False            
                 
        def synthetic(self, stepper1_target, segmentTicks, segmentKey, absoluteMove, sync):
            if(len(self.virtualNode.syntheticMotionBuffer)<= self.virtualNode.motionBufferSize): #space available in buffer
                self.virtualNode.syntheticMotionBuffer.appendleft({'stepper1_target':stepper1_target, 'segmentTicks':segmentTicks, 'segmentKey': segmentKey,
                                                                   'absoluteMove':absoluteMove, 'sync':sync})
                self.virtualNode.syntheticWritePosition += 1
                if(self.virtualNode.syntheticWritePosition == self.virtualNode.motionBufferSize):
                    self.virtualNode.syntheticWritePosition = 0
                return {'statusCode':1, 'currentKey': self.virtualNode.syntheticCurrentKey, 'ticksRemaining': self.virtualNode.syntheticTicksRemaining, 
                        'readPosition': self.virtualNode.syntheticReadPosition, 'writePosition': self.virtualNode.syntheticWritePosition}
            else:
                return {'statusCode':0, 'currentKey': self.virtualNode.syntheticCurrentKey, 'ticksRemaining': self.virtualNode.syntheticTicksRemaining, 
                        'readPosition': self.virtualNode.syntheticReadPosition, 'writePosition': self.virtualNode.syntheticWritePosition}            

    class getPositionRequest(core.actionObject):
        """Returns the absolute position of the stepper motor."""
        def init(self):
            if self.transmitUntilResponse():
                return self.getPacket()['stepper1_absolutePosition']
            else:
                notice(self.virtualNode, 'Unable to get absolute position!')
                return False  

        def synthetic(self):
            return {'stepper1_absolutePosition':self.virtualNode.syntheticStepperPositions[0]}
                       
            
    class stepStatusRequest(core.actionObject):
        def init(self):
            """Returns the current motion status of the node.
            
            Returns a dictionary containing the following keys:
                statusCode -- will always read 1 to a spinStatusRequest. In the context of the response to a spin request, indicates whether the move was queued successfully.
                currentKey -- Each motion segment is assigned a sequential ID to confirm nothing has been lost. This will return the key of the motion segment currently
                              under the buffer read head.
                timeRemaining -- The time remaining in the current move, in seconds.
                readPosition -- The current position of the read head, which is the buffer location that was last read.
                writePosition -- The current position of the write head, which is the buffer location that was last written.
            """
            if self.transmitUntilResponse():
                response = self.getPacket()
                response.update({'timeRemaining':units.s(self.virtualNode.stepGenUnits(response.pop('ticksRemaining')))}) #convert time remaining into seconds
                return response
            else:
                notice(self.virtualNode, 'Unable to get spin status!')
                return False
        
        def synthetic(self):
            return {'statusCode':1, 'currentKey': self.virtualNode.syntheticCurrentKey, 'ticksRemaining': self.virtualNode.syntheticTicksRemaining, 
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
                    virtualNode.syntheticTicksRemaining = currentMove['segmentTicks']
                    virtualNode.syntheticReadPosition += 1
                    if(virtualNode.syntheticReadPosition == virtualNode.motionBufferSize):
                        virtualNode.syntheticReadPosition = 0
                    time.sleep(units.s(self.stepGenUnits(virtualNode.syntheticTicksRemaining)))
                    if(currentMove['absoluteMove']):
                        relativeMotion = currentMove['stepper1_target'] - virtualNode.syntheticStepperPositions[0]
                    else:
                        relativeMotion = currentMove['stepper1_target']
                    virtualNode.syntheticStepperPositions[0] += relativeMotion
            time.sleep(0.001)
            

# TEST CODE HERE
if __name__ == "__main__":
    config.syntheticModeOn()
#     config.verboseDebugOn()
    stepperNode1 = virtualNode()
    stepperNode2 = virtualNode(interface = stepperNode1._interface_)
    time.sleep(0.5)
    
#     syncToken = core.syncToken()
#     syncToken.push(hello = 5, goodbye = 3)
#     syncToken.push(goodbye = 8)
#     print syncToken.pullMaxValue('goodbye')
#     print syncToken.pullMinValue('goodbye')
#     exit()
#     stepperNode.setMotorCurrent(0.67)
    position = 0
    for i in range(10):
#         stepperNode.stepRequest(i*25, i*25*128, sync = i%2)
#         stepperNode.stepRequest(i*25, i*25*32, sync = True)
        stepperNode1.stepRequest(2, 24*16*0.0000625, sync = True)
        stepperNode2.stepRequest(2, 24*16*0.0000625, sync = True)
        position += 2
    time.sleep(1)
    for i in range(10):
        syncRequest = stepperNode1.syncRequest()
        syncRequest.commit()
        syncRequest.clearForRelease()
        print "SYNC"
#         time.sleep(6)
    print "--- TARGET POSITION: " + str(position)
    while True:
        print stepperNode1.getPositionRequest()
        time.sleep(0.25)      
        