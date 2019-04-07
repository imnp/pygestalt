// COMMUNICATIONS SPEED TEST - GESTALT NODE
//
// April 6th, 2019
// Ilan E. Moyer
//
//---- INCLUDES ----

#include <gestalt.h>
#include <avr/io.h>
#include <util/delay.h>

// ---- HEADERS ----

//---- DEFINE IO ----


//CONFIGURE URL
char myurl[] = "http://www.fabunit.com/vn/gestaltNode_commTest.py";

//--- GESTALT PORT DEFINITIONS ---
#define testPacketPort    10

//---- PARAMETERS ----
// The below parameters are actually defined in the gestalt library, but to avoid name-space issues are not broken out publicly.
uint8_t lengthLocation = 4;
uint8_t basePacketLength = 5;

//USER SETUP
void userSetup(){
  setURL(&myurl[0], sizeof(myurl));
}

void userLoop(){
};

// ---- UTILITY FUNCTIONS ----

// ---- SERVICE ROUTINES ----
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

// ---- PACKET ROUTER ----
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
