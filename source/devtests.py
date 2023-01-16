# Testing code used during development

from pygestalt import packets
from pygestalt import utilities
# from pygestalt import core
# from pygestalt import nodes
from pygestalt import config
# from pygestalt import interfaces
from pygestalt import units
from pygestalt import geometry
from pygestalt import mechanics
from pygestalt import plotting
from pygestalt import simulation

import copy
import time

# Define Packets
# payloadTestPacket = packets.template('port5Default')
# payloadTestPacket = packets.template('payloadTestPacket',
#                                      packets.unsignedInt('xPosition', 2),
#                                      packets.signedInt('yPosition', 2),
#                                      packets.fixedPoint('pressureSensor', 0,16),
#                                      packets.pString('URL'))
# 
# gestaltPacket = packets.template('gestaltPacketTemplate',
#                                        packets.unsignedInt('_startByte_',1),
#                                        packets.unsignedInt('_address_', 2),
#                                        packets.unsignedInt('_port_', 1),
#                                        packets.length('_length_'),
#                                         packets.packet('_payload_'),
#                                        packets.checksum('_checksum_'))
# 
# 
#  
# payloadDict = {'xPosition':1025, 'yPosition':-1024, 'pressureSensor':-0.99999, 'URL':'www.fabunit.com'}
# encodedPayloadPacket = payloadTestPacket.encode(payloadDict)

# fixedPointTestPacket = packets.template('fixedTest',
#                                         packets.fixedPoint('pressureSensor', 1,11))
# encodedPacket = fixedPointTestPacket.encode({'pressureSensor':0.95})
# decimalValue = utilities.bytesToUnsignedInteger(encodedPacket)
# print decimalValue
# print fixedPointTestPacket.decode(encodedPacket)

# bitFieldTestPacket = packets.template('bitFieldTest',
#                                       packets.bitfield('myBitField', 8, (0,'bitO', True),
#                                                                         (1,'bit1', True),
#                                                                         (2,'bit2', True),
#                                                                         (3,'bit3', True),
#                                                                         (4,'bit4', False),
#                                                                         (5,'bit5', False),
#                                                                         (6,'bit6', False),
#                                                                         (7,'bit7', False)))
# encodedPacket = bitFieldTestPacket.encode({'myBitField':{'bit0':True,'bit1':False, 'bit2':True,'bit3':False,'bit4':True, 'bit5':False,'bit6':True}})
# print encodedPacket
# 
# print bitFieldTestPacket.decode(encodedPacket)



#  
# gestaltDict = {'_startByte_':72, '_address_':1, '_port_':72, '_payload_':encodedPayloadPacket}
# gestaltDict = {'_startByte_':72, '_address_':1, '_port_':72, '_payload_':[]}
# encodedGestaltPacket = gestaltPacket.encode(gestaltDict)
# print encodedGestaltPacket[0:3]
# print gestaltPacket.decodeTokenInIncompletePacket('_port_', encodedGestaltPacket[0:4])

# exit()
# myEncodedPacket = [72, 1, 0, 72, 25, 1, 4, 0, 252, 1, 128, 119, 119, 119, 46, 102, 97, 98, 117, 110, 105, 116, 46, 99, 111, 109, 203]
# print gestaltPacket.validateChecksum('_checksum_', myEncodedPacket)
# 
# decodedGestaltPacket, remainder = gestaltPacket.decode(encodedGestaltPacket)
# 
# decodedPayloadPacket, remainder = payloadTestPacket.decode(decodedGestaltPacket['_payload_'])

# embeddedTestPacket = packets.template('embeddedTestPacket',
#                                       packets.unsignedInt('zPosition',2),
#                                       packets.packetTemplate('myTemplate', payloadTestPacket),
#                                       packets.fixedPoint('temperatureSensor', 0, 15))
# 
# embeddedDict = copy.copy(payloadDict)
# 
# embeddedDict.update({'zPosition':7272, 'temperatureSensor':0.501})
# 
# encodedEmbeddedPacket = embeddedTestPacket.encode(embeddedDict)
# gestaltDict['_payload_'] = encodedEmbeddedPacket
# encodedGestaltPacket = gestaltPacket.encode(gestaltDict)
# 
# decodedGestaltPacket = gestaltPacket.decode(encodedGestaltPacket)[0]
# gestaltPayload = decodedGestaltPacket['_payload_']
# 
# gestaltPayloadStartIndex, gestaltPayloadEndIndex, gestaltPayloadToken = gestaltPacket.findTokenPosition('_payload_', encodedGestaltPacket)
# searchedPayload = encodedGestaltPacket[gestaltPayloadStartIndex:gestaltPayloadEndIndex]
# print searchedPayload
# 
# decodedEmbeddedPacket = embeddedTestPacket.decode(searchedPayload)[0]
# 
# startIndex, endIndex, token = embeddedTestPacket.findTokenPosition('temperatureSensor', searchedPayload)
# print token.decode(searchedPayload[startIndex: endIndex])[0]

# class getTuna(core.actionObject):
#     def init(self, name):
#         self.name = name
#         return self.classInfo
# 
# getTuna.classInfo = "hello"
# x = getTuna('charlie')
# print x

# config.syntheticModeOn()    #turn on synthetic mode

# # The code below tests whether actionObject classes are being copied

# serialInterface = interfaces.serialInterface()
# serialInterface.connect()


# gestaltInterface = interfaces.gestaltInterface('myGestaltInterface', interface = serialInterface)
# 
# 
# config.verboseDebugOn()
# myGestaltNode = nodes.arduinoGestaltNode(name = "myGestaltNode", port = "/dev/tty.usbmodem1451")
# myGestaltNode = nodes.gestaltNodeShell(name = "myGestaltNode", interface = serialInterface)
# myGestaltNode = nodes.gestaltNodeShell(name = "myGestaltNode")
# print myGestaltNode._virtualNode_
# myGestaltNode = nodes.arduinoGestaltVirtualNode(name = "myGestaltNode", port = "/dev/tty.usbmodem1451")
# myGestaltNode = nodes.arduinoGestaltNode(name = "myGestaltNode", port = "/dev/tty.usbmodem1451")
#   
# print myGestaltNode.statusRequest()


   
#    
# print myGestaltNode.bootWriteRequest(pageNumber = 0, data = range(128))
# print myGestaltNode.bootReadRequest(pageNumber = 127)
# print myGestaltNode.urlRequest()
# print myGestaltNode.setAddressRequest(1025)
# print myGestaltNode.synNodeAddress
# print myGestaltNode.identifyRequest()
# print myGestaltNode.resetRequest()
# print myGestaltNode
# class myGestaltNode(nodes.gestaltNode):
#     def init(self):
#         print "myGestaltNode init"
#     def onLoad(self):
#         print "myGestaltNode onLoad"
         

# --UNITS--
# myNumber = units.mm(1.243)
# myNumberTwo = units.mm(0.5)
# myNumberThree = units.mm(2)
# 
# print myNumberThree * myNumberThree
# print myNumberThree ** 2

# baseUnits, conversion = units.getBaseUnits(units.yd)
# print baseUnits.fullName
# print conversion

# unitDict = units.unitDictionary({units.m:1, units.s:-2})
# unitDict2 = unitDict / {units.s:2, units.m:-1}
# print unitDict2
# 
# unitDict3 = 1/unitDict
# print unitDict3
# 
# unitDict4 = unitDict**3
# print unitDict4

# float1 = units.m(1.45)
# float2 = units.s(4.5)
# print (float1*float2)
# 
# float3 = units.N*units.m/units.s**2
# print(float3)

# float1 = 4.44*units.m
# print float1
# float2 = 7.77*units.s
# print float2

# print float1 / float2

# mySpeed = 100*units.m/units.s**2
# 
# print mySpeed.convert(units.m/units.min**2)

# ---- TESTING REVISED UNIT DICTIONARY

# print("Check Unit String")
# print(units.m)

# print("Check Unit Representation")
# print(repr(units.m))

# print("Unit Multiplication")
# work = units.m * units.N

# print(work)
# print(repr(work))

# print("Unit Division")
# velocity = units.m/units.s

# distance = velocity * units.s

# print(velocity)
# print(repr(velocity))

# print("Check unitary units: m/s * s")
# print(repr(distance))

# print("Check dFloat generation")
# print(1.5*velocity)
# print(velocity*1.5)
# print(1.5/velocity)
# print(velocity/1.5)

# bikeSpeed = velocity(5.8)
# print(bikeSpeed)
# print(bikeSpeed*units.s(2))
# print(bikeSpeed/units.s(2))

# # Test unit conversion
# inch_velocity = units.inch / units.min
# metric_velocity = units.m / units.s

# print(repr(inch_velocity))
# print(repr(metric_velocity))

# print(metric_velocity.getBaseUnitDictionary())
# print(inch_velocity.getBaseUnitDictionary())

# watts = units.unit("W", "Watts", units.N*units.m/units.s, 1)
# print(repr(watts))

# joules = watts * units.s

# print(joules)

# print(joules.getBaseUnitDictionary())

# power_english = units.unit("PE", "Power English", units.lbf * units.ft / units.s, 1)
# print(repr(power_english))

# energy_english = power_english*units.s
# print(energy_english.getBaseUnitDictionary())

# # Test unitdict equivilency functions
# velocity1 = units.m/units.s
# velocity2 = units.deg*units.inch/units.min

# vel1_unitdict, conversion = velocity1.getBaseUnitDictionary()
# vel2_unitdict, conversion = velocity2.getBaseUnitDictionary()

# print("vel1:" + str(vel1_unitdict))
# print("vel2:" + str(vel2_unitdict))

# print(vel1_unitdict == vel2_unitdict)

# # Test Conversion

# distance_m = units.m(2)

# print(units.inch(distance_m))


# print(units.rad(units.deg(360)))

# print((units.m/units.s)((units.ft/units.min)(5)))
# print(units.g.isCompoundUnit())

# print(repr(units.rad/units.s))


# ---MECHANICS---
# myArray = geometry.array([[1,2,3],[4,5,6],[7,8,9]])
# print myArray[0,1]
# print type(myArray[0,:])

# print units.mm/units.rev

# myLeadscrew = mechanics.leadscrew(units.rev(10)/units.inch(1))
# print myLeadscrew.forwardTransform
# print myLeadscrew.forward(360*units.deg)
# print myLeadscrew.reverse(0.25*units.inch)
# print myLeadscrew.transform(360*units.deg)
# print myLeadscrew.transform(units.mm(2.54))

# myGearbox = mechanics.gear(5)
# print myGearbox.forward(units.rad(6.28*5))
# print myGearbox.reverse(units.deg(72))

# myTimingBelt = mechanics.timingBelt(18)
# print myTimingBelt.forward(units.rev(1))

# myStepperMotor = mechanics.stepperMotor(units.step(400)/units.rev(1))
# print myStepperMotor.forward(units.step(200))

# myLeadscrew = mechanics.leadscrew(units.mm(10)) #define a leascrew with a pitch of 10mm
# myGearbox = mechanics.gear(2)  #define a gearbox with a ratio of 2:1
# myStepper = mechanics.stepper(units.step(200)/units.rev(1)) #define a stepper motor with 200 steps per rev
#  
# xAxisChain = mechanics.chain(myStepper, myGearbox, myLeadscrew)
# yAxisChain = mechanics.chain(mechanics.stepper(1.8), mechanics.gear(2), mechanics.leadscrew(10))
# 
# actuators = mechanics.stack(xAxisChain, yAxisChain)

# 
# print xAxisChain.reverse(units.mm(10))
# print xAxisChain.forward(units.step(100))
# print yAxisChain.forward(units.step(200))
# print actuators.getSize()
# print actuators.forward([units.step(100), units.step(200)])
# print actuators.reverse([units.mm(2.5), units.mm(5)])
# 
# testStack = mechanics.stack(xAxisChain)
# print testStack.forward(units.step(100))
# print testStack.reverse(units.mm(2.5))
# 
# myCoreXY = mechanics.corexy()
# print myCoreXY.forward([1,1])
# print myCoreXY.reverse([1,0])

# aAxis = mechanics.chain( mechanics.stepper(1.8), mechanics.timingBelt(9.6))
# bAxis = mechanics.chain(mechanics.stepper(1.8), mechanics.timingBelt(9.6))
# cAxis = mechanics.chain(mechanics.stepper(1.8), mechanics.rack(5))
# coreXY = mechanics.corexy()

# kinematics = mechanics.chain(mechanics.stack(aAxis, bAxis, cAxis), mechanics.stack(mechanics.corexy(), mechanics.passThru(1)))
# print kinematics.reverse([units.mm(100), units.mm(100), units.mm(30)])

# outputOffset = mechanics.offset(3)
# kinematics2 = mechanics.chain(mechanics.stack(aAxis, bAxis, cAxis), mechanics.stack(mechanics.corexy(), mechanics.passThru(1)), mechanics.router([0,2,1]), outputOffset)
# print kinematics2.reverse([units.mm(100), units.mm(30), units.mm(100)])
# print kinematics2.reverse([units.mm(100), units.mm(100), units.mm(30)])
# print kinematics2.forward([units.step(1326), units.step(0), units.step(381)])

# outputOffset.adjust([-100, -30, -100])

# print kinematics2.forward([units.step(1326), units.step(0), units.step(381)])

## ----array addition and subtraction--------
# myArray1 = geometry.array([[1,2,3,4],[4,3,2,1]])
# myArray2 = geometry.array([[5,6,6,5],[8,7,6,5]])
# 
# print geometry.arrayAddition(myArray1, myArray2)
# print geometry.arraySubtraction(myArray1, myArray2)
# print " "
# print myArray1 + myArray2
# print myArray1 + [[5,6,6,5], [8,7,6,5]]
# print [[5,6,6,5], [8,7,6,5]] + myArray1
# print myArray1 - [[5,6,6,5], [8,7,6,5]]
# print [[5,6,6,5], [8,7,6,5]] - myArray1




# 
# matrix1 = geometry.matrix([[2,-2],[5,3]])
# matrix2 = geometry.matrix([[-1,4],[7,-6]])
# print matrix1
# print matrix1.transpose()
# print matrix1*matrix2
# print geometry.dotProduct(matrix1, matrix2)

# exit()
# myList = geometry.array([[1,2,3],[4,5,6],[7,8,9]])
# myList2 = myList[:,0]
# print isinstance(myList, list)
# print "size: " + str(myList.getSize())
# print "dimension: " + str(myList.getDimension())

# myMatrix = geometry.matrix([1,2,3])
# matrix1 = geometry.matrix([[2,-2],[5,3]])
# matrix4 = geometry.matrix([[units.mm(1)],[units.mm(1)]])

# 
# print myMatrix[0]
# 
# # 
# print matrix1
# print matrix1.getSize()
# # 
# # 
# newMatrix =  matrix1[0,:]
# print newMatrix
# 
# exit()
# 
# print newMatrix[0]

# matrix3 = matrix1*matrix4
# matrix3 = matrix3 * 10
# print matrix3[1,0]

# matrix4 = geometry.matrix([[3,8],[4,6]])
# x = geometry.testClass()
# x[1:,2:]
# print matrix4.determinant()
# print myList[1,1]

# time.sleep(2)

# myArray = geometry.array([[1,2,3],[4,5,6],[7,8,9]])
# print myArray.getSize()
# print myArray.getDimension()
# print geometry.indexIntoArray(myArray, (2,2))
# print myArray[0]
# 
# myArray2 = geometry.array([[1,2,3]])
# print myArray2
# print myArray2[1:]

# matrix1 = geometry.matrix([[2,-2],[5,3]])
# matrix2 = geometry.matrix([[-1,4],[7,-6]])
# print matrix1
# print matrix1.transpose()
# print matrix1*matrix2
# print matrix1.concatenateRight(matrix2)
# print matrix1.concatenateLeft(matrix2)

# matrix5 = geometry.matrix([[units.mm(1),units.mm(2)],[units.mm(3),units.mm(4)]])

# print geometry.arrayMultiplyByScalar(matrix5, 2)
# print matrix5[:,:0]

# matrix6 = geometry.matrix(geometry.matrixInverse(matrix5))
# print matrix6
# print matrix6[0,0]

# matrix7 = geometry.matrix([[units.mm(4),units.mm(2),units.mm(8)],[units.mm(7),units.mm(3),units.mm(9)],[units.mm(2),units.mm(6),units.mm(7)]])
# print matrix7.inverse()[0,0]


# print geometry.dotProduct(matrix1, matrix2)
# matrix8 = geometry.matrix([[1,2,3],[4,5,6],[7,8,9]])
# matrix9 = matrix8 * units.mm(1.0)
# print matrix9[0,0]

##----- Persistence -----

# persistenceManager = utilities.persistenceManager(filename = "../persistenceTest.vmp", namespace = 'myName')
# 
# persistenceManager['hello'] = [5,6,7]
# print persistenceManager['hello']
# 
# persistenceManager.set('goodbye', 'wuzzup')
# print persistenceManager.get('goodbye')

##----- Function Distributor -----

# class tester(object):
#     def test(self, arg1, arg2, arg3, arg4 = None, arg5 = None, sync = None):
#         return arg5

# test1 = tester()
# test2 = tester()
# test3 = tester()
# print(core.distributedFunctionCall('owner', [test1, test2, test3], 'test', core.syncToken, 'arg1', 'arg2', 1, arg4 = "arg4", arg5 = ("arg51", "arg52", "arg53")))


##------ PLOTTING -------

# x = plotting.dataset([(1,1),(3,3),(5,7)], (units.s, units.m))
# x.plot()

##------ SIMULATION ------
# simulation.clearpath_CPM_SDSK_3411P_RLN.power_curve().plot()

# units.m(3)**-1

aAxis = mechanics.rotaryPulley(1.0)
load = simulation.load((units.oz*units.inch**2)(3.9))
# print(aAxis.forward(units.rev(3)))

testSystem = simulation.system(simulation.clearpath_CPM_SDSK_3411P_RLN, aAxis, load)
print(testSystem.reflectedInertia())

# print(1/units.rad**2)
