# Testing code used during development

from pygestalt import packets

# addressToken = packets.unsignedInt('address',2)
# myPacket = packets.template('myPacket', addressToken)
# 
# print addressToken.encode({'address': 1025})

myPacket = packets.template('myPacket', packets.unsignedInt('address',2),
                                        packets.unsignedInt('port',1),
                                        packets.unsignedInt('length',1))

myPacket2 = packets.template('myPacket2', packets.unsignedInt('address',2),
                                        packets.unsignedInt('port',1),
                                        packets.unsignedInt('length',1))

print myPacket.encode({'address':1032, 'port':34, 'length':74})