## CRC-8 Checksum Algorithm

Checksums are a useful technique for verifying that a sequence of bytes has been received exactly as it was transmitted. pyGestalt uses a simple 8-bit checksum, generated using the CRC-8 algorithm. 

The first step of this algorithm is to pre-generate a 256-byte lookup table. This allows us to minimize the number of cycles required to generate or validate the CRC in the tranceiver interrupt routines, which is important so as not to bog down the microcontroller.

### Table Generation

The below algorithm will generate each byte in a 256-byte long lookup table. _**Importantly, the "tap polynomial" is 0b00000111 (or simply 7) for the CRC-8 algorithm.**_
```python
def calculateByteInCRCTable(self, byteValue):
  polynomial = 7 #for CRC-8
  for i in range(8):
    byteValue = byteValue << 1
    if (byteValue//256) == 1:
      byteValue = byteValue - 256
      byteValue = byteValue ^ polynomial
  return byteValue
```

The above function should be fed sequentially with the indices of each byte in the table:
```python
def crcTableGen(self):
  self.crcTable = []
  for i in range(256):
    self.crcTable += [self.calculateByteInCRCTable(i)]
```

The resulting table looks like this:

```python
crcTable = [0, 7, 14, 9, 28, 27, 18, 21, 56, 63, 54, 49, 36, 35, 42, 45, 112, 119, 126, 121, 108, 107, 98, 101, 72, 79, 70, 65, 84, 83, 90, 93, 224, 231, 238, 233, 252, 251, 242, 245, 216, 223, 214, 209, 196, 195, 202, 205, 144, 151, 158, 153, 140, 139, 130, 133, 168, 175, 166, 161, 180, 179, 186, 189, 199, 192, 201, 206, 219, 220, 213, 210, 255, 248, 241, 246, 227, 228, 237, 234, 183, 176, 185, 190, 171, 172, 165, 162, 143, 136, 129, 134, 147, 148, 157, 154, 39, 32, 41, 46, 59, 60, 53, 50, 31, 24, 17, 22, 3, 4, 13, 10, 87, 80, 89, 94, 75, 76, 69, 66, 111, 104, 97, 102, 115, 116, 125, 122, 137, 142, 135, 128, 149, 146, 155, 156, 177, 182, 191, 184, 173, 170, 163, 164, 249, 254, 247, 240, 229, 226, 235, 236, 193, 198, 207, 200, 221, 218, 211, 212, 105, 110, 103, 96, 117, 114, 123, 124, 81, 86, 95, 88, 77, 74, 67, 68, 25, 30, 23, 16, 5, 2, 11, 12, 33, 38, 47, 40, 61, 58, 51, 52, 78, 73, 64, 71, 82, 85, 92, 91, 118, 113, 120, 127, 106, 109, 100, 99, 62, 57, 48, 55, 34, 37, 44, 43, 6, 1, 8, 15, 26, 29, 20, 19, 174, 169, 160, 167, 178, 181, 188, 187, 150, 145, 152, 159, 138, 141, 132, 131, 222, 217, 208, 215, 194, 197, 204, 203, 230, 225, 232, 239, 250, 253, 244, 243]
```

### Calculating the CRC Value for a Packet
Because we pre-generated the CRC table, it's almost trivial to calculate the CRC for a given sequence of bytes.

Take the below sequence:

```python
sequence = [72, 26, 106, 10, 8, 3, 3, 3]
```

We apply the following algorithm to the sequence:

```python
crc = 0
for byte in sequence:
  crcByte = byte^crc
  crc = crcTable[crcByte]
```

The resultant CRC value is 114, and the entire packet (with the CRC appended) would look like this:

```
packet = [72, 26, 106, 10, 8, 3, 3, 3, 114]
```

### Validating the Packet
The process for validating the packet is actually identical. You feed the packet thru the same algorithm:

```python
crc = 0
for byte in packet:
  crcByte = byte^crc
  crc = crcTable[crcByte]
```

_**The CRC value should be 0 if the packet is valid!**_ Otherwise, one of the bytes in the packet has changed since the CRC byte was generated.

