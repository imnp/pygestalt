## Communications Protocol

### Standard Gestalt Packet Frame
All communications between the pyGestalt virtual nodes and Gestalt-based physical nodes rely on the standard Gestalt packet format, shown below:

|Byte Position|Description                      |
|-------------|---------------------------------|
|Byte 0       |Start Byte _(72 = unicast, 138 = multicast)_|
|-------------|---------------------------------|
|Byte 1       |Destination Address _(Byte 0)_     |
|-------------|---------------------------------|
|Byte 2       |Destination Address _(Byte 1)_     |
|-------------|---------------------------------|
|Byte 3       |Destination Port                 |
|-------------|---------------------------------|
|Byte 4       |Packet Length                    |
|-------------|---------------------------------|
|Byte 5 -> N-1|Payload                          |
|-------------|---------------------------------|
|Byte N       |Checksum                         |
|-------------|---------------------------------|

- **Start Byte**: Besides beginning the packet, this byte also defines whether the packet is _unicast_ or _multicast_. A unicast packet will only be received by the node whose address matches that specified in the packet. A multicast packet, on the other hand, will be received by all nodes on the Gestalt network.
- **Destination Address**: Each node on the Gestalt network is assigned a unique two-byte address, which is mirrored in the corresponding virtual node. In this way, messages can be routed back and forth between a virtual node and its physical counterpart.
- **Destination Port**: Just as addresses are used to pair virtual and physical nodes, port numbers are used to pair individual service routines. For example, a service routine in the virtual node on Port 10 would communicate to a corresponding firmware service routine on Port 10. The port number is a single byte. _**Ports 1-9 and 255 are reserved by the Gestalt library.**_
- **Packet Length**: The total length of the packet _**minus 1**_, in bytes. For example, a packet consisting of 15 bytes total (including the payload), would have a length byte equal to 14.
- **Payload**: A variable-length payload. This is used to transmit data between service routines on the virtual and physical nodes. It is possible (and common) for the payload to have zero length.
- **Checksum**: A checksum generated from the sequence of bytes in the packet, and used to guarantee that the packet has not become corrupted in transmission. Gestalt uses the _**[CRC-8 checksum algorithm](crc8.md)**_.

### Serial Communication Protocol
Gestalt nodes typically communicate over a asynchronous serial connection, often via a USB-to-serial converter. The format is 8 data bits, no parity bits, and 1 stop bit.

#### Standard Baud Rates

|Node Type                  |Baud Rate      |
|---------------------------|---------------|
|Standard Gestalt Node      |115.2 kbps     |
|---------------------------|---------------|
|Arduino-Based Gestalt Node |38.4 kbps      |
|---------------------------|---------------|

The standard baud rates above were based on the clock frequency of the microcontroller. Custom Gestalt nodes use a 18.432Mhz crystal, which was selected to have zero rate error at 115.2kbps (and all standard baud rates). Because Arduinos rely on a 16Mhz crystal, communication speeds are limited by the rate error. A non-standard speed of 76.8kbps would have been ideal, but is unsupported in Linux. Therefore, we use a standard baud rate of 38.4 kbps. This has a rate error of 0.2%.

