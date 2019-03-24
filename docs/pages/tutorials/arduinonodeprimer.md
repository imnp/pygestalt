## My First Arduino pyGestalt Node

### Introduction
In this tutorial, we will walk you step-by-step through the process of creating an Arduino-based _physical node_ and a complementary Python-based _virtual node_. By the end of the tutorial, you will be able to write firmware for your own custom nodes, and then import and interact with them from any Python program.

We're going to start with a few basic examples that touch on various aspects of the framework: 
1. Turn on and off the built-in LED from a Python program. 
2. Blink the LED a certain number of times, and cause the Python program to wait until complete.
3. Do some arithmatic on the Arduino, and return the result.


### Materials
- An Atmega328-based Arduino, like the [Arduino Uno]()
- USB A to B cable

### Prerequisites
- Install / register the Gestalt firmware library with your Ardunio IDE.

### Part 1: Blink an LED -- Quick-Start
_We're going to show you how to write your own custom nodes on both the firmware and Python sides. But first, we'd like to give you the chance to jump to the end and use our pre-written example code to get a flavor of the end goal. This will also help you make sure you have all of the elements configured correctly, including the Arduino IDE, your Python environment, and the pyGestalt library._


### Part 2: Blink an LED -- Writing the Firmware
#### 2.1 Fire up the Arduino IDE
This part is self-explanatory, but go ahead and initialize a new sketch in the Arduino IDE.
_We typically write nodes with a certain structure, so that we don't forget any steps. In this tutorial we'll walk you thru each section individually._ 

#### 2.2 Specify Includes
The *includes* section is where you'll tell the IDE which libraries to include when compiling your code. We only need two for this tutorial:
{% highlight c %}
// ---- INCLUDES ----
#include <gestalt.h>
#include <util/delay.h>
{% endhighlight %}
- gestalt.h is the header file for the Gestalt library, and is required for every node.
- delay is the standard Arduino delay library

#### 2.3 Assign URL
Every Gestalt node has a complementary Python virtual node. It is possible to publish these Python files online, and pyGestalt will automatically download and import them. This is similar to automatically downloading drivers for new hardware. In the URL section, we define a custom URL where the virtual node can be found. For now, we'll just use something imaginary. _Keep in mind that we take no responsibility for security issues that might arise when you automatically download and execute Python files from the internet._
{% highlight c %}
// ---- URL ----
char myurl[] = "http://www.fabunit.com/vn/examples/arduino_basicNode.py";
{% endhighlight %}

#### 2.4 Define Gestalt Ports
Virtual and physical node functions are connected by _ports_. These are simply mutually-agreed upon internal addresses assigned to each Gestalt function, where messages can be sent and received. Ports 0-9 and 255 are reserved by the Gestalt firmware library, but you are free to assign ports 10-254 as you wish.

{% highlight c %}
// ---- GESTALT PORTS ----
#define LEDControlPort    10 
{% endhighlight %}

#### 2.5 IO Definitions
It can be cleaner to define all pin definitions in one place, which we will do here. Note that we're going to use the bare-metal AVR C pin definitions. Bear with us! We'll show you how to set pin directions and state without using the somewhat bloated Arduino functions.

{% highlight c %}
//---- IO DEFINITIONS ----

// LED
#define LED_DIR		DDRB	//Controls the pin direction
#define LED_PORT 	PORTB	//Controls the output state of the pin
#define LED_PIN		PINB	//Used to read input state
#define LED_pin		5 	//PB5. We use just the number b/c Arduino doesn't define the pin.
{% endhighlight %}

- DDRB is an internal register that controls pin direction
- PORTB is an internal register that controls pin output state.
- PINB is an internal register that reads pin state.
- PB5 is the IO pin to which Arduino has an LED already pre-wired.

#### 2.6 User Setup
The Gestalt library commandeers Arduino's setup() function, but instead provides us with userSetup(). This is called once, towards the beginning of program execution. It's where you'll put any code needed to configure the node.

{% highlight c %}
//---- USER SETUP ----
void userSetup(){
  setURL(&myurl[0], sizeof(myurl)); //Registers URL with Gestalt library
  LED_DIR |= (1<<LED_pin); //Set the LED pin direction as an output
  LED_PORT &= ~(1<<LED_pin); //Turn off the LED
};
{% endhighlight %}

- First, we explicitly register the URL with the Gestalt library
- Next, we set the direction of the LED pin to an output. All we're doing is saying "set the bit corresponding to the LED\_pin, while not altering anything else." This is accomplished by bit-shifting a 1 into the LED\_pin position, and then writing it to the port with an OR-EQUALS operator.
- Finally, we make sure the LED starts out being off. This is accomplished similarly to the above, but since we're clearing the bit instead of setting it, we first invert the byte and then use the AND-EQUALS operator.

Although this method of setting and clearing individual bits might seem complicated, it becomes pretty routine once you get used to the pattern.

#### 2.7 Main User Loop
Just like the standard Arduino setup() function, loop() is needed by the Gestalt library. You can put any code that runs in a loop inside userLoop(). Our userLoop() will be empty for these examples.

{% highlight c %}
//---- USER LOOP ----
void userLoop(){
};
{% endhighlight %}

#### 2.8 User Packet Router
When messages arrive at the node, they need to be routed to the correct _service routine_ based on the port to which they are addressed. userPacketRouter() is called whenever a message arrives, with the target port number as the only argument. This is really the switch-board that connects your physical node to its virtual counterpart.

{% highlight c %}
//---- USER PACKET ROUTER ----
void userPacketRouter(uint8_t destinationPort){
  switch(destinationPort){
    case LEDControlPort: //a message was sent to the LED port
      svcControlLED(); //call the LED control service routine
      break;
    // add additional case statements for new ports here, following the pattern immediately above.
  }
};
{% endhighlight %}

#### 2.9 Utility Functions
Typically there's some tasks that are repetitive or error-prone to reproduce throughout the code, so we write small "utility" functions to handle them. For example, turning on or off an LED, stepping a motor (or changing it's direction), etc. For this example, we have utility functions for turning on and off the LEDs.

{% highlight c %}
//---- UTILITY FUNCTIONS ----
void ledOn(){
 	// Turns on the indicator LED
  	LED_PORT |= (1<<LED_pin); //Turn on the LED	
}

void ledOff(){
 	// Turns off the indicator LED
  	LED_PORT &= ~(1<<LED_pin); //Turn off the LED
};
{% endhighlight %}

#### 2.10 Service Routines
Messages arrive from the virtual node and must be received, interpreted, and executed upon by the physical node. We call the function that does this a _service routine_. Most service routines not only receive a message, but also respond as well; maybe something as simple as an empty packet to acknowledge receipt, or a payload laden with e.g. a sensor reading. Here we write a simple service routine to turn on or off the LED, depending on the received payload. After receipt, an "empty" paycket -- meaning one with no data payload -- is transmitted in reply.


{% highlight c %}
//---- SERVICE ROUTINES ----
// These are functions that get called by the userPacketRouter function
// when a message is received over the gestalt interface.
void svcControlLED(){
	uint8_t command = rxBuffer[payloadLocation]; //first byte of payload
	if(command){ //check if command is non-zero
		ledOn(); //yes; turn LED on
	}else{
		ledOff(); //no; turn LED off
	};
	
	transmitUnicastPacket(LEDControlPort, 0); //transmit an empty (0 payload bytes) unicast packet to the LEDControlPort
};
{% endhighlight %}

- First, we read the first _payload_ (data) byte from the _Receive Buffer_. This buffer is a reserved area of memory used to record message bytes as they arrive. The data section of the message -- meaning the actual content of the message rather than the preamble or closing bytes -- starts at the  keyword *payloadLocation* that is defined by the Gestalt firmware library. In our case, the payload is a single byte instructing the node whether to turn on or off the LED. When we write the pyGestalt virtual node, we'll show you how to build this packet.
- Next, we simply check whether the LED command byte is zero or non-zero, indicating whether to turn off or on the LED, respectively. Using our utility functions, we then make it happen.
- Finally, we send a return message to the virtual node (VN). This indicates receipt, and can also be used to pause program execution on the VN side until the command is executed. If turning on or off the LED required communicating with an external controller, you might consider returning a single "success" byte as part of the response message.

_And that's it for the physical node firmware! Continue on to learn how to write the virtual node._
 
### Part 3: Blink an LED -- Writing the Virtual Node
_Here we will show you how to write a corresponding Python module -- what we call the *virtual node* -- that can be imported into your Python scripts in order to directly control the physical node. We will follow a similar format to writing the physical node firmware; each relevant section of the code will be handled individually. By the end, you'll have a complete end-to-end control system for turning on and off an LED._

#### 3.1 Fire up a Python code editor
Create a new Python file in your favorite text editor. We use Eclipse (so passe, we know!), but you could use really anything. Sublime Text is also quite nice and does helpful syntax highlighting. You'll need to name the file "arduino_basicNode.py" so that it matches the filename specified in the physical node's URL (or adjust per Section 2.3 above to your own taste).

#### 3.2 Imports Section
The only modules you need to import are a couple pyGestalt sub-modules.
{% highlight python %}
#---- IMPORTS -----
from pygestalt import nodes
from pygestalt import core
from pygestalt import packets
{% endhighlight %}
- _pygestalt.nodes_ gives you access to the pyGestalt virtual node base classes
- _pygestalt.core_ provides access to the actionObject class for creating service routines
- _pygestalt.packets_ for access to the packet templates and encoding types

#### 3.3 _virtualNode_ Class
All of the code for your virtual node should live inside a _virtualNode_ class.
{% highlight python %}
class virtualNode(nodes.arduinoGestaltVirtualNode):
	"""The arduino_basicNode virtual node."""
{% endhighlight %}
- the class **must** be called "virtualNode" in order for consistency, and for it to be automatically imported correctly within the context of a virtual machine.
- The base class of this particular node should be _nodes.arduinoGestaltVirtualNode_. This takes care of a lot of configuration for you, including setting the correct commnications baud rate.

#### 3.4 _init_ Function
The virtual node base class overrides the standard _\_\_init\_\__() function, and instead provides _init()_. This is called when the virtual node is first initialized, and gets passed any (non-reserved) arguments provided on initialization of the virtual node. This is a good place to define any parameters relevant to the specific node.
{% highlight python %}
    def init(self, *args, **kwargs):
        """Initialiation method for the virtual node instance."""
        self.crystalFrequency = 16000000    #MHz
        self.ADCReferenceVoltage = 5.0  #Volts
{% endhighlight %}

The above are just examples of parameters you might typically put in the init() function, although are not immediately relevant to the LED control example. If you don't want to put anything in _init()_, simply don't declare it, or make this the first and only line in the function:
{% highlight python %}
    def init(self, *args, **kwargs):
        """Initialiation method for the virtual node instance."""
        pass
{% endhighlight %}

#### 3.5 _initPackets_ Function
As a communications framework, one of the primary tasks of pyGestalt is to make it easier to pass various data types back and forth between the virtual node and the firmware running on the physical node. Data is transmitted via _packets_, which are sequences of bytes that follow a specific format. Gestalt packets contain a fixed number of framing bytes, and then a variable number of _payload_ bytes. The _packets_ sub-module helps you define and encode these packet payloads with a rich set of data types. For the purposes of our example, we'll define a simple packet for transmitting an on/off control signal to the Arduino via a single data byte.
{% highlight python %}
    def initPackets(self):
        """Initialize packet types."""
        self.LEDControlRequestPacket = packets.template('LEDControlRequest',
                                                           packets.unsignedInt('command',1))
{% endhighlight %}
The packet template is defined with several arguments:
- A name for the template, used for logging and reporting errors
- An unlimited number of additional arguments, each containing _packetTokens_ from the pygestalt.packets submodule. The sequence of these tokens defines how they are ordered in the packet payload. Each token has a mandatory name - used to reference the token inside the packet - and any additional parameters needed to set up the token. In our example, we're transmitting a single unsigned value to the physical node, encoded within one byte of payload data.

#### 3.6 _initPorts_ Function
In order for service routine functions in the virtual node to communicate with the service routines on physical node, they must both have a commonly shared identifier (referred to in pyGestalt as a port), and a common understanding of how transmitted information is encoded. self.bindPort() "binds" virtual node service routines to port numbers, and then associated them with the packet templates that are used to encode and decode transmitted communication packets. With these associations in place, pyGestalt is able to automatically assist in shuttling messages in the correct format between virtual and physical nodes.

{% highlight python %}
    def initPorts(self):
        """Bind functions to ports and associate with packets."""
        self.bindPort(port = 10, outboundFunction = self.LEDControlRequest, outboundTemplate = self.LEDControlRequestPacket)
{% endhighlight %}
- _self.bindPort_ is an internal function of the _virtualNode_ base class
- the _port_ argument specifies a port number. This must match the associated port number provided to _userPacketRouter_ in the physical node firmware.
- _outboundFunction_ is the virtual node service routine responsible for controlling the LED. We haven't written this yet, but will be doing so in a few steps.
- _outboundTemplate_ is the packet template - defined in the prior section - that is responsible for encoding the message to the physical node.
- Note that we don't specify an inbound template, because the response from the physical node is an "empty" acknowledgement containing no payload data.

#### 3.7 Public User Functions
This is the section where we write functions that are explicitly intended for the user to call. These are useful in situations like our LED demo, where the user might want to simply call ledOn() or ledOff(), rather than calling the service routine that actually transmits the command to the physical node. (If this doesn't make sense yet, read ahead to the next section). Note that these functions should be indented so that they are at the same level as all of the init functions we just wrote.

{% highlight python %}
    def ledOn(self):
        """Turns on the LED on the physical node."""
        return self.LEDControlRequest(True) #simply calls the virtual node service routine with a True (meaning "on") argument
    
    def ledOff(self):
        """Turns off the LED on the physical node."""
        return self.LEDControlRequest(False) #calls the virtual node service routine with a False (meaning "off") argument
{% endhighlight %}

#### 3.8 Service Routines
Virtual node service routines are functions that are responsible for communicating with complementary service routines on the physical node. These special functions are actually children of the actionObject base class. We won't go into all of the details here, but pyGestalt follows a pattern where calls to service routines do not simply generate encoded packets. Rather, an actionObject is generated and preserved until the very moment before transmission, at which point it spits out an encoded packet. The short reason for this is that for more complicated controls applications, such as those requiring motion planning, the final output of the function might change well after it is first called.
{% highlight python %}
    class LEDControlRequest(core.actionObject):
        """Controls the state of the node's indicator LED."""
        def init(self, ledState):
            """Initializes the actionObject.
            
            ledState -- a boolean value, where True will turn on the LED, and False will turn it off.

            Returns True if a confirmation packet was received, or False if not.
            """
            if ledState:
                self.setPacket(command = 1)
            else:
                self.setPacket(command = 0)
                            
            if self.transmitUntilResponse(): #Transmits multiple times if necessary until a reply is received from the node.
                return True #A response was received, so indicate the command was executed by returning True.
            else: #No response was received, in spite of multiple attempts.
                notice(self.virtualNode, 'got no respone to LED control request') #generate a notice to the user.
                return False
{% endhighlight %}
