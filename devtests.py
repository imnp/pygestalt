# Testing code used during development

from pygestalt import packets

# addressToken = packets.unsignedInt('address',2)
# myPacket = packets.template('myPacket', addressToken)
# 
# print addressToken.encode({'address': 1025})

gestaltPacket = packets.template('gestaltPacket', packets.unsignedInt('_startByte_',1),
                                        packets.unsignedInt('_address_',2),
                                        packets.unsignedInt('_port_',1),
                                        packets.length('_length_'),
                                        packets.packet('_payload_'),
                                        packets.checksum('_checksum_'))

myPacket = packets.template('myPacket', packets.unsignedInt('xPosition',2),
                                        packets.unsignedInt('yPosition',2),
                                        packets.unsignedInt('zPosition',2))


myEncodedPacket = myPacket.encode({'xPosition':1023, 'yPosition':1024,'zPosition':1025 })
print gestaltPacket.encode({'_startByte_':72, '_address_':1024, '_port_':34, '_payload_': myEncodedPacket})

# myPacket = packets.template('myPacket', packets.pString('URL'))

# myEncodedPacket = myPacket.encode({'URL':"HTTP://WWW.FABUNIT.COM"})
# print gestaltPacket.encode({'_startByte_':72, '_address_':1024, '_port_':34, '_payload_': myEncodedPacket})
# print gestaltPacket.encode({'_startByte_':72, '_address_':1024, '_port_':34, '_payload_': myEncodedPacket}).toString()

myPackets2 = packets.template('myPacket2', myPacket)

myEncodedPacket2 = myPackets2.encode({'xPosition':1023, 'yPosition':1024,'zPosition':1025 })
print gestaltPacket.encode({'_startByte_':72, '_address_':1024, '_port_':34, '_payload_': myEncodedPacket})