# Testing code used during development

from pygestalt import packets
from pygestalt import utilities

# Define Packets

gestaltPacket = packets.template('gestaltPacketTemplate',
                                       packets.unsignedInt('_startByte_',1),
                                       packets.unsignedInt('_address_', 2),
                                       packets.unsignedInt('_port_', 1),
                                       packets.length('_length_'),
                                       packets.packet('_payload_'),
                                       packets.checksum('_checksum_'))

payloadTestPacket = packets.template('payloadTestPacket',
                                     packets.unsignedInt('xPosition', 2),
                                     packets.signedInt('yPosition', 2),
                                     packets.fixedPoint('pressureSensor', 0,15),
                                     packets.pString('URL'))

payloadDict = {'xPosition':1025, 'yPosition':-1024, 'pressureSensor':-0.99999, 'URL':'www.fabunit.com'}
encodedPayloadPacket = payloadTestPacket.encode(payloadDict)

gestaltDict = {'_startByte_':72, '_address_':1, '_port_':72, '_payload_':encodedPayloadPacket}
encodedGestaltPacket = gestaltPacket.encode(gestaltDict)

decodedGestaltPacket, remainder = gestaltPacket.decode(encodedGestaltPacket)

decodedPayloadPacket, remainder = payloadTestPacket.decode(decodedGestaltPacket['_payload_'])

print decodedPayloadPacket