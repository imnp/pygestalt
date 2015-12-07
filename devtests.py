# Testing code used during development

from pygestalt import packets
from pygestalt import utilities
from pygestalt import core
from pygestalt import nodes
from pygestalt import config
from pygestalt import interfaces
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

# serialInterface = interfaces.serialInterface('/dev/tty.usbmodem1451')
# gestaltInterface = interfaces.gestaltInterface('myGestaltInterface', interface = serialInterface)
# 
# 
# config.verboseDebugOn()
# myGestaltNode = nodes.arduinoGestaltNode(name = "myGestaltNode", port = "/dev/tty.usbmodem1451")
# myGestaltNode = nodes.gestaltNodeShell(name = "myGestaltNode", interface = serialInterface)
# myGestaltNode = nodes.gestaltNodeShell(name = "myGestaltNode")
# print myGestaltNode._virtualNode_
myGestaltNode = nodes.arduinoGestaltVirtualNode(name = "myGestaltNode", port = "/dev/tty.usbmodem1451")
# myGestaltNode = nodes.arduinoGestaltNode(name = "myGestaltNode", port = "/dev/tty.usbmodem1451")
#   
print myGestaltNode.statusRequest()
   
   
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
         

time.sleep(2)