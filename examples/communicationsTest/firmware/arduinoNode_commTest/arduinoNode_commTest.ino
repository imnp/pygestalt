//---- INCLUDES ----
#include <gestalt.h>
#include <util/delay.h>

//--- URL ---
char myurl[] = "http://www.fabunit.com/vn/examples/arduinoNode_commTest.py"; //URL that will be reported to virtual node on acquisition

//--- GESTALT PORT DEFINITIONS ---
#define testPacketPort    10

//---- IO DEFINITIONS ----
// Here's where you define all of your inputs and outputs.

//---- PARAMETERS ----
// The below parameters are actually defined in the gestalt library, but to avoid name-space issues are not broken out publicly.
uint8_t lengthLocation = 4;
uint8_t basePacketLength = 5;

//---- USER SETUP ----
void userSetup(){
  // The Gestalt version of the typical Arduino setup() function. Put anything here that you want to be called
  // just once on startup.
  setURL(&myurl[0], sizeof(myurl)); //Registers URL with Gestalt library
};

//---- USER LOOP ----
void userLoop(){
  // The Gestalt version of the typical Arduino loop() function. Code placed here will be called in an infinite loop.
};

//---- UTILITY FUNCTIONS ----
// This is where we typically put functions that make life (or code) simpler, like
// turning on or off an LED, stepping a stepper motor, etc...


//---- SERVICE ROUTINES ----
// These are functions that get called by the userPacketRouter function
// when a message is received over the gestalt interface.
void svcTestPacket(){
	// Returns a test packet
	// The number of payload bytes in the response is encoded in the first byte of the received payload.
	// However, we need to be careful to handle a zero-length payload properly.
 
	uint8_t receivedPayloadLength = rxBuffer[lengthLocation] - basePacketLength; //total length of payload
	if(receivedPayloadLength > 0){
		uint8_t requestedPayloadLength = rxBuffer[payloadLocation]; //requested length is encoded in the payload bytes
		transmitUnicastPacket(testPacketPort, requestedPayloadLength);
	}else{
		transmitUnicastPacket(testPacketPort, 0); //transmit an empty response
	};
};


//---- USER PACKET ROUTER ----
void userPacketRouter(uint8_t destinationPort){
  // This function is responsible for calling the appropriate service routine for a given inbound packet.
  //    destinationPort -- the port number of the inbound packet
  
  switch(destinationPort){
    case testPacketPort: //a message was sent to the test packet port
      svcTestPacket(); //call the test packet service routine
      break;
    // add additional case statements for new ports here, following the pattern immediately above.
  }
};
