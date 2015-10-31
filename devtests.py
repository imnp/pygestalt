# Testing code used during development

from pygestalt import packets
from pygestalt import utilities
from pygestalt import core
from pygestalt import nodes
import copy

# Define Packets
# payloadTestPacket = packets.template('port5Default')
gestaltPacket = packets.template('gestaltPacketTemplate',
                                       packets.unsignedInt('_startByte_',1),
                                       packets.unsignedInt('_address_', 2),
                                       packets.unsignedInt('_port_', 1),
                                       packets.length('_length_'),
                                       packets.packet('_payload_'),
                                       packets.checksum('_checksum_'))
# 
# payloadTestPacket = packets.template('payloadTestPacket',
#                                      packets.unsignedInt('xPosition', 2),
#                                      packets.signedInt('yPosition', 2),
#                                      packets.fixedPoint('pressureSensor', 0,15),
#                                      packets.pString('URL'))
# 
# payloadDict = {'xPosition':1025, 'yPosition':-1024, 'pressureSensor':-0.99999, 'URL':'www.fabunit.com'}
# encodedPayloadPacket = payloadTestPacket.encode(payloadDict)
# 
# gestaltDict = {'_startByte_':72, '_address_':1, '_port_':72, '_payload_':encodedPayloadPacket}
gestaltDict = {'_startByte_':72, '_address_':1, '_port_':72, '_payload_':[]}
encodedGestaltPacket = gestaltPacket.encode(gestaltDict)
print encodedGestaltPacket
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



# # The code below tests whether actionObject classes are being copied

myGestaltNode = nodes.baseGestaltNode()
print core.genericOutboundActionObjectBlockOnReply._port_

myGestaltNode.bindPort(5)
