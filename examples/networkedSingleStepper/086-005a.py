# SINGLE AXIS NETWORKED STEPPER NODE
# 086-005a
# Re-written for pyGestalt 0.7
#
# July 7th, 2018
# Ilan E. Moyer

#---- IMPORTS ----
from pygestalt import nodes, core, packets, utilities, interfaces, config, units
from pygestalt.utilities import notice
import time
import math

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
        self.maxSteps = 255 #maximum number of steps per packet (1 byte)
        self.clockFrequency = 184320000.0 #1/s, crystal clock frequency
        self.stepGenClockTicks = 921.0 #number of system clock ticks per step interrupt
        self.uStepsPerStep = 1048576  #not to be confused with microstepping. This is the number of internal uSteps before a physical step is triggered.
        self.uTimeUnit = float(self.stepGenClockTicks) / self.clockFrequency #the time per step gen interrupts, in seconds
        
        # AXES
        self.size = 1 #number of axes
        
        # SYNTHETIC PARAMETERS
        self.syntheticMotorCurrentReferenceVoltage = 0 #this is set to match the current request inside setMotorCurrent()
        self.syntheticMotorEnableFlag = 0 #tracks whether the motor is enabled when in synthetic mode.
        self.syntheticUVelocity = 0 #the current uStep rate in synthetic mode.
        self.syntheticCurrentKey = 0
        self.syntheticStepsRemaining = 0
        self.syntheticReadPosition = 0
        self.syntheticWritePosition = 0
        
        
    def initPackets(self):
        """Initializes all packet definitions"""
        
        self.readCurrentReferenceVoltageResponsePacket = packets.template('readCurrentReferenceVoltageResponse',
                                                                          packets.unsignedInt('vrefValue',2)) #the raw ADC value of the driver voltage reference
        
        self.spinRequestPacket = packets.template('spinRequest',
                                                  packets.unsignedInt('majorSteps', 1),
                                                  packets.unsignedInt('directions', 1),
                                                  packets.unsignedInt('steps', 1),
                                                  packets.unsignedInt('accel', 1),
                                                  packets.unsignedInt('accelSteps', 1),
                                                  packets.unsignedInt('decelSteps', 1),
                                                  packets.unsignedInt('sync', 1))
        
        self.spinStatusPacket = packets.template('spinStatus',
                                                 packets.unsignedInt('statusCode', 1),
                                                 packets.unsignedInt('currentKey', 1),
                                                 packets.unsignedInt('stepsRemaining', 1), #steps remaining in the current move
                                                 packets.unsignedInt('readPosition', 1), #position of the read head
                                                 packets.unsignedInt('writePosition', 1)) #position of the write head
        
        self.setVelocityRequestPacket = packets.template('setVelocityRequest',
                                                         packets.unsignedInt('uStepRate', 2))
    
    def initPorts(self):
        """Binds functions and packets to ports"""
        
        self.bindPort(port = 20, outboundFunction = self.readCurrentReferenceVoltageRequest, inboundPacket = self.readCurrentReferenceVoltageResponsePacket)
        self.bindPort(port = 21, outboundFunction = self.enableRequest)
        self.bindPort(port = 22, outboundFunction = self.disableRequest)
        self.bindPort(port = 23, outboundFunction = self.spinRequest, outboundPacket = self.spinRequestPacket, inboundPacket = self.spinStatusPacket)
        self.bindPort(port = 24, outboundFunction = self.setVelocityRequest, outboundPacket = self.setVelocityRequestPacket)
        self.bindPort(port = 26, outboundFunction = self.spinStatusRequest, inboundPacket = self.spinStatusPacket)
        self.bindPort(port = 30, outboundFunction = self.syncRequest)
    
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
        
        
    class enableRequest(core.actionObject):
        def init(self):
            """Enables the motor driver, causing the stepper coils to become energized.
            
            Returns True if successful, or False otherwise.
            """
            if self.transmitUntilResponse():
                notice(self.virtualNode, 'Stepper Motor Enabled.')
                return True
            else:
                notice(self.virtualNode, 'Failed to Enable Stepper Motor!')
                return False
    
        def synthetic(self):
            self.virtualNode.syntheticMotorEnableFlag = 1
            return {}
    
    
    class disasbleRequest(core.actionObject):
        def init(self):
            """Disables the motor driver, removing power to the stepper motor coils.
            
            Returns True if successful, or False otherwise.
            """
            if self.transmitUntilResponse():
                notice(self.virtualNode, 'Stepper Motor Disabled.')
                return True
            else:
                notice(self.virtualNode, 'Failed to Disable Stepper Motor!')
                return False
    
        def synthetic(self):
            self.virtualNode.syntheticMotorEnableFlag = 0
            return {}    
    
            
    class setVelocityRequest(core.actionObject):
        def init(self, velocity):
            """Sets the step rate of the virtual major axis.
            
            velocity -- the step rate of the virtual major axis, in steps/second
            
            This command will be run asynchronously, meaning that the step rate will be changed as soon as
            the command has been called. It is also worth mentioning that this step rate applies to THE VIRTUAL MAJOR
            AXIS. During synchronized moves, individual motors may spin at different rates in proportion to the
            number of steps they are taking relative to the virtual major axis.
            """
            
            # We need to convert velocity in steps/sec, into the number of uSteps that the microcontroller should take per interrupt.
            # Velocity (steps/sec) * uStepsPerStep (uSteps/step) * uTimeUnit (sec/interrupt) = uSteps/interrupt
            # Note that the result is divided by 16 so as to fit comfortably inside a 16-bit word. It is multiplied back in firmware.
            
            uStepsPerInterrupt = int(round((velocity * self.virtualNode.uStepsPerStep * self.virtualNode.uTimeUnit)/16.0))
            
            self.setPacket(uStepRate = uStepsPerInterrupt)
            if self.transmitUntilResponse():
                return True
            else:
                notice(self.virtualNode, 'Unable to set velocity!')
                return False
        
        def synthetic(self, uStepRate):
            self.virtualNode.syntheticUVelocity = uStepRate
            return {}
            
            
    class spinStatusRequest(core.actionObject):
        def init(self):
            """Returns the current motion status of the node.
            
            Returns a dictionary containing the following keys:
                statusCode -- will always read 1 to a spinStatusRequest. In the context of the response to a spin request, indicates whether the move was queued successfully.
                currentKey -- Each motion segment is assigned a sequential ID to confirm nothing has been lost. This will return the key of the motion segment currently
                              under the buffer read head.
                stepsRemaining -- The number of steps remaining in the current move.
                readPosition -- The current position of the read head, which is the buffer location that was last read.
                writePosition -- The current position of the write head, which is the buffer location that was last written.
            """
            if self.transmitUntilResponse():
                return self.getPacket()
            else:
                notice(self.virtualNode, 'Unable to get spin status!')
                return False
        
        def synthetic(self):
            return {'statusCode':1, 'currentKey': self.virtualNode.syntheticCurrentKey, 'stepsRemaining': self.virtualNode.syntheticStepsRemaining,
                    'readPosition': self.virtualNode.syntheticReadPosition, 'writePosition': self.virtualNode.syntheticWritePosition}
            
        