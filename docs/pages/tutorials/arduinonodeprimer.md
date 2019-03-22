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
_We're going to show you how to write your own custom nodes on both the firmware and Python sides. But first, we'd like to give you the chance to jump to the end and use our pre-written example code to get a flavor of the end goal. This will also help you make sure you have all of the elements configured correctly, including the Arduino IDE, your Python environment, and the pyGestalt library.


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
 