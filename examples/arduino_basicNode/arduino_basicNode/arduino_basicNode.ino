//---- INCLUDES ----
#include <gestalt.h>
#include <util/delay.h>

//--- URL ---
// When a physical node is associated with a virtual node, the physical node reports a URL pointing to where the
// virtual node file can be found online. This allows the author of the physical node to publish a virtual node
// 'driver' online, and have it automatically loaded by the Gestalt framework.
char myurl[] = "http://www.fabunit.com/vn/examples/arduino_basicNode.py"; //URL that will be reported to virtual node on acquisition

//--- GESTALT PORT DEFINITIONS ---
// Once a packet has been received by the node, it is directed to a specific service routine handler. A port number
// is used to associate the packet with its handler. Ports 0 -> 9 and 255 are reserved by the gestalt firmware library,
// but you are free to use any other port.
#define LEDControlPort    10 

//---- IO DEFINITIONS ----
// Here's where you define all of your inputs and outputs.

// LED
#define LED_DIR		DDRB	//Controls the pin direction
#define LED_PORT 	PORTB	//Controls the output state of the pin
#define LED_PIN		PINB	//Used to read input state, and set pull-ups
#define LED_pin		5 		//PB5

//---- USER SETUP ----
void userSetup(){
  // The Gestalt version of the typical Arduino setup() function. Put anything here that you want to be called
  // just once on startup.
  setURL(&myurl[0], sizeof(myurl)); //Registers URL with Gestalt library
  LED_DIR |= (1<<LED_pin); //Set the LED pin direction as an output
  LED_PORT &= ~(1<<LED_pin); //Turn off the LED
};

//---- USER LOOP ----
void userLoop(){
  // The Gestalt version of the typical Arduino loop() function. Code placed here will be called in an infinite loop.
};

//---- UTILITY FUNCTIONS ----
// This is where we typically put functions that make life (or code) simpler, like
// turning on or off an LED, stepping a stepper motor, etc...
void ledOn(){
 	// Turns on the indicator LED
  	LED_PORT |= (1<<LED_pin); //Turn on the LED	
}

void ledOff(){
 	// Turns off the indicator LED
  	LED_PORT &= ~(1<<LED_pin); //Turn off the LED	
}

//---- SERVICE ROUTINES ----
// These are functions that get called by the userPacketRouter function
// when a message is received over the gestalt interface.
void svcControlLED(){
	//Turns on or off the LED, depending on the value of the first payload byte in the receive buffer.
	
	uint8_t command = rxBuffer[payloadLocation]; //first byte of payload
	if(command){ //check if command is non-zero
		ledOn(); //yes, turn LED on
	}else{
		ledOff();
	};
	
	transmitUnicastPacket(LEDControlPort, 0); //transmit an empty (0 payload bytes) unicast packet to the LEDControlPort
};
	

//---- USER PACKET ROUTER ----
void userPacketRouter(uint8_t destinationPort){
  // This function is responsible for calling the appropriate service routine for a given inbound packet.
  //    destinationPort -- the port number of the inbound packet
  
  switch(destinationPort){
    case LEDControlPort: //a message was sent to the LED port
      svcControlLED(); //call the LED control service routine
      break;
    // add additional case statements for new ports here, following the pattern immediately above.
  }
};
