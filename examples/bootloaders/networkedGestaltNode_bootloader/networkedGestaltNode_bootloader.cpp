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
char myurl[] = "http://www.fabunit.com/vn/genericNetworkedGestaltBootloader.py";

//--- GESTALT PORT DEFINITIONS ---

//---- PARAMETERS ----

//USER SETUP
void userSetup(){
  setURL(&myurl[0], sizeof(myurl)); //set URL

  // -- NETWORKED GESTALT PIN CONFIGURATIONS --
  // LED for associating virtual and physical nodes
  IO_ledPORT = &PORTB;
  IO_ledDDR = &DDRB;
  IO_ledPIN = &PINB;
  IO_ledPin = 1<<3; //PB3

  // button for associating virtual and physical nodes
  IO_buttonPORT = &PORTB;
  IO_buttonDDR = &DDRB;
  IO_buttonPIN = &PINB;
  IO_buttonPin = 1<<2; //PB2

  // UART transmit and receive pins
  IO_txrxPORT = &PORTD;
  IO_txrxDDR = &DDRD;
  IO_rxPin = 1<<0; //PD0
  IO_txPin = 1<<1; //PD1

  // RS-485 driver enable pin
  IO_txEnablePORT = &PORTD;
  IO_txEnableDDR = &DDRD;
  IO_txEnablePin = 1<<2; //PD2
}

void userLoop(){
};

// ---- UTILITY FUNCTIONS ----

// ---- SERVICE ROUTINES ----


// ---- PACKET ROUTER ----
void userPacketRouter(uint8_t destinationPort){
  // This function is responsible for calling the appropriate service routine for a given inbound packet.
  //    destinationPort -- the port number of the inbound packet
};
