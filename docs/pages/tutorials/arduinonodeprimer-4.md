## My First Arduino pyGestalt Node (continued...)

### Part 4: Bi-directional Communication
_We'll now show you how implement bi-directional communication with the node. To illustrate, we'll create a new service routine on the Arduino that simply adds two numbers together and returns the result._

#### 4.1 Add New Packet Definitions to Virtual Node
_If our goal is for the Arduino to add two numbers, we need a way of both transporting those numbers to the Arduino, and then returning the result. To do this we'll create both outbound and inbound packet templates._

The following packet template objects should be added to the virtual node's _initPackets()_ function:
 ```python
self.additionRequestPacket = packets.template('additionRequest',
                                                    packets.fixedPoint('input1', 6, 10),
                                                    packets.fixedPoint('input2', 6, 10)) #5 integer bits + sign, 10 fractional
        
self.additionResponsePacket = packets.template('additionResponse',
                                                    packets.fixedPoint('result', 6, 10))
 ```

We've also introduced the _fixedPoint_ packet token. This will allow us to send decimal values to the Arduino and have them operated on. The notation of the input parameters is a bit tricky. The "6" is the number of integer bits, _including_ the sign bit. The "10" is the number of fractional bits to the right of the decimal point. We can therefore transmit values that range between approximately 31.999 and -31.999, with a resolution of about 0.001. As an aside, you won't need to worry about this on the firmware side, because in this example the Arduino will simply add the two numbers without worrying about where the decimal point is located.

#### 4.2 Bind a New Port in Virtual Node
We now need to connect a new service routine (which we'll write next) to a new port number, and to the packet templates above. Add the following function call to the virtual node's _initPorts()_ function:
 ```python
self.bindPort(port = 11, outboundFunction = self.sumNumbers, outboundTemplate = self.additionRequestPacket,
              inboundTemplate = self.additionResponsePacket)
 ```

#### 4.3 Write the Virtual Node Service Routine
Let's now write the virtual node's service routine function which can be called by the user to add two numbers together. It should:
1. Accept two numbers as input arguments
1. Transmit these numbers to the physical node
1. Wait for a reply
1. Return a result

The following function should be added to the service routine section of the virtual node:

 ```python
class sumNumbers(core.actionObject):
    """Remotely sums two numbers and returns the result."""
    def init(self, value1, value2):
        """Initializes the actionObject.
        
        value1 -- the first number to be added
        value2 -- the second number to be added
        
        Returns value1 + value2
        """
        self.setPacket(input1 = value1, input2 = value2)
        
        if self.transmitUntilResponse(): #Transmits multiple times if necessary until a reply is received from the node.
            result = self.getPacket()['result'] #retrieves the result from the response packet
            return result #return the result
        else: #didn't receive a response from the node
            notice(self.virtualNode, 'got no response to addition request') #generate a notice to the user.
            return False
 ```

 _We are now done modifying the virtual node. Let's move on to write the necessary firmware functionality._
 
#### 4.4 Define a New Port Number in the Firmware
Modify the _Gestalt Ports_ section to include a new entry:
 ```c
#define LEDControlPort    10
#define sumPort			  11
 ```
Of course, the new port number must match what we used in the virtual node.

#### 4.5 Add a New Entry to the User Packet Router
Modify the **_userPacketRouter()_** function to include a new _case_ statement:

 ```c
 void userPacketRouter(uint8_t destinationPort){
  // This function is responsible for calling the appropriate service routine for a given inbound packet.
  //    destinationPort -- the port number of the inbound packet
  
  switch(destinationPort){
    case LEDControlPort: //a message was sent to the LED port
      svcControlLED(); //call the LED control service routine
      break;
    case sumPort: //a message was sent to the sum port
      svcSumNumbers(); //call the number addition service routine
      break;
    // add additional case statements for new ports here, following the pattern immediately above.
  }
  ```

#### 4.6 Write the Number Summing Service Routine

Here's where the action happens! Add the following function to the Service Routine section:
 ```c
 void svcSumNumbers(){
   // Sums two numbers and returns the result.
   int16_t value1 = (int16_t)((uint16_t)rxBuffer[payloadLocation] + 
				(((uint16_t)rxBuffer[payloadLocation+1])<<8)); //read in value1 from rxBuffer
   int16_t value2 = (int16_t)((uint16_t)rxBuffer[payloadLocation+2] + 
				(((uint16_t)rxBuffer[payloadLocation+3])<<8)); //read in value2 from rxBuffer
  
   int16_t result = value1 + value2; //sum inputs
  
   txBuffer[payloadLocation] = (uint8_t)(result & 0x00FF); //write out result
   txBuffer[payloadLocation+1] = (uint8_t)((result & 0xFF00)>>8);

   transmitUnicastPacket(sumPort, 2); //transmit the result as a unicast packet
};
 ```
- First, this function unpacks the signed fixed-point numbers stored in the receiver payload buffer. This is perhaps the trickiest part of the function, as these bytes need to be handled correctly by the compiler. Bytes are encoded in the packet as "little-endian", meaning that the least significant byte comes first. We cast each received byte within an encoded number as an unsigned integer, bit-shift according to the position of the byte in the encoded number (e.g. x1, x256, etc), and then sum all of the bit-shifted bytes. Lastly, we re-cast the sum as a signed integer. The magic of fixed-point notation is that the Arduino will do the same math, regardless of the position of the decimal point.
- We then sum the numbers. This is easy enough!
- Next, we pack the result back into an outgoing payload. This is pretty much the reverse process of unpacking, and involves masking and then bit-shifting the summation result according to position of each byte in the encoded number.
- Finally, we transmit the result in a unicast packet, containing a two-byte payload.

#### 4.7 Try It Out!
In a terminal, navigate to the directory containing the virtual node. Then run the following commands:
 ```python
 >> python
 >>> import arduino_basicNode as arduino
 >>> myArduino = arduino.virtualNode()
 >>> myArduino.sumNumbers(1.25,-8.72)
 ```

You should very quickly receive the following result:
 ```
 -7.4697265625
 ```

While the exact answer is of course -7.47, the error is caused by quantization of both the inputs and the result. This was a lot of work to just sum a couple numbers. But it is kinda cool that we just did some remote math! And now you know how to set up bi-directional communication between a virtual and physical node.

#### 4.8 Bonus: Remote Math Using a Python Script

Let's say you want to use your Arduino for a lot of remote math. Instead of typing the terminal commands each time, you can add them to a python script. Check out the below Python script (also in the example file _remoteAddition.py_):

```python
import arduino_basicNode as arduino #import the virtual node module, with an easier name
import sys #for getting input arguments

inputValues = sys.argv  #contains all of the arguments provided when the script was called.

value1 = float(sys.argv[1]) #first input argument, converted from string to float
value2 = float(sys.argv[2]) #second input argument, converted from string to float

myArduino = arduino.virtualNode()
print myArduino.sumNumbers(value1, value2)
```

Now, from the terminal, run the python script with a couple values you want to sum:
```bash
python remoteAddition.py 10.8 4.8
```

Should return:
```bash
15.599609375
```