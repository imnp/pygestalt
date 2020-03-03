// SINGLE AXIS NETWORKED STEPPER DRIVER
//
// A pyGestalt Framework Project by IMNP.
//
//  --REVISION HISTORY---------------------------------
//
//  --------------------------------------------------------------------------------------------------------
//  | DATE    | MODIFICATIONS                            | NAME              | FILENAME                    |
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |09/03/13 | CREATED                                  | ILAN E. MOYER     | 086-005a.cpp                |
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |04/13/19 | MODIFIED FOR pyGestalt 0.7. Major change |					 |							   |
//  |         | includes switch to absolute positioning. | ILAN E. MOYER     | 086-001b.cpp	           	   |
//  --------------------------------------------------------------------------------------------------------
//
//  ----- IMPORTANT NOTES -----
//  Since the first networked single axis stepper driver was introduced in 2013, it has been used in
//  hundreds of machine-building projects. This "B" revision marks a fundamental shift in the way the
//  node operates. Previously, all motion commands were sent as relative "step" commands that were
//  synchronized using a "virtual major axis" approach. This had several downsides, which included
//  a) only incremental relative motion commands could be supported, and b) other types of nodes,
//  even those that did not involve motors, needed to run a step generator in the background in order
//  to synchronize. We are now switching to using TIME as the synchronizing parameter. The epiphany
//  of sorts which makes this possible is that rather than dividing number of steps by time to yield a
//  step rate, we're simply using clock time directly in the bresenham algorithm (instead of a virtual
//  major axis). The result is that it should be much easier to build diverse node types that function
//  in the same system, and in the near-term we'll be able to support absolute positioning.
//  These changes, and a switch to pyGestalt 0.7, makes 086-005b incompatible with 086-005a. However,
//  we believe that it is worthwhile in order to make the node more useful and robust.

//  ----- INCLUDES -----
#include <stdlib.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>
#include <gestalt.h>

//  ----- HEADERS -----
void enableStepGenerator();
void disableStepGenerator();
void steppers_enterReset();
void steppers_exitReset();
void resetAllDrivers();
void stepper1_enableDriver();
void stepper1_disableDriver();
void disableAllDrivers();
void enableAllDrivers();
void stepper1_forward();
void stepper1_reverse();


//  ----- IO DEFINITIONS -----
//  -- STEPPER 1 --
#define stepper1_PORT			PORTC
#define stepper1_DDR			DDRC
#define stepper1_PIN			PINC
#define stepper1_Step			PC0
#define stepper1_Direction		PC1
#define stepper1_Reset			PC2		// Active low driver reset
#define stepper1_MS1			PC3
#define stepper1_MS0			PC4
#define stepper1_Enable			PC5		// Active low driver enable
#define stepper1_vRef			7		// ADC7


//  ----- GESTALT PORT DEFINITIONS -----
#define gestaltPort_sync			8 	// Triggers a sync. This is a proxy for the sync control line.
#define gestaltPort_getVRef 		11	// Read current reference
#define gestaltPort_enableDrivers	12	// enables or disables stepper driver
#define gestaltPort_stepRequest		13  // steps a relative number of steps, or to an absolute position
#define gestaltPort_getPosition		14	// returns the current absolute position
#define gestaltPort_getStatus		15	// returns the current node status

//  ----- STEPPING PARAMETERS -----
#define defaultHardwareMicrostepping		3	// 0b00: Full, 0b01: Half, 0b10: Quarter, 0b11: Sixteenth -- NOTE: this is set manually on a per-bit basis in userSetup()
#define smoothingMicrosteppingBits			2   // The number of bits of microstepping used purely for smoothing. The positioning step resolution is quarter-steps.
#define numberOfSteppersOnNode				1 	// Only one stepper on the node

//  ----- STEP GENERATOR PARAMETERS -----
#define stepGenerator_timeBase				1152		// clock ticks per call of step generator.
														// At 18.432MHz, this is a period of 62.5us, or 16KHz.
														// timeBase = 1000 @ 16MHz, and 1250 @ 20MH

//  ----- STEP GENERATOR STATE VARIABLES -----
struct stepperState{
	volatile uint32_t stepsRemaining; //the number of steps remaining on this stepper in the active motion segment. This is only used for reporting.
	volatile uint32_t targetSteps; //the target number of steps on this stepper in the active motion segment
	volatile int32_t bresenhamAccumulator; //each tick, targetSteps is added to this accumulator.
	volatile int8_t direction; //stores the direction in which the stepper is moving, for updating position
};

volatile struct stepperState activeSegment_stepperStates[numberOfSteppersOnNode]; //array of stepper motors, to support more than one motor on a node.
volatile int32_t activeSegment_bresenhamTriggerThreshold = 0; //the clock tick count threshold to trigger a step. This is the segment time / 2 (per bresenham algorithm)
volatile uint32_t activeSegment_timeRemaining = 0; //keeps track of how much time is remaining in the active segment
volatile uint32_t activeSegment_totalTime = 0; //total time of the segment, for the bresenham algorithm
volatile uint8_t activeSegment_segmentKey = 0; //the key of the current segment
volatile uint8_t waitingForSync = 0; //if 1, then waiting on a synchronization packet


//  ----- POSITION STATE VARIABLES -----
volatile int32_t stepperPositions[numberOfSteppersOnNode] = {0};		// the current position of each stepper, in microsteps

//  ----- MOTION BUFFER -----
struct motionSegment{ //11 bytes
  volatile int32_t stepper_target[numberOfSteppersOnNode]; //either target number of steps, or target absolute position
  volatile uint32_t segmentTime; //execution time of the segment, in motion ticks (units of 62.5us)
  volatile uint8_t segmentKey; //a rolling key counter that identifies the active segment
  volatile uint8_t absoluteMove; //0: incremental, 1: absolute
  volatile uint8_t waitForSync; //0: cleared to run this segment, 1: wait for synchronization signal
};

const uint8_t motionBuffer_length = 48;  //528 bytes, on an atmega32x total memory is 2K. This is approximately 0.75 seconds of move data with one node on network.
volatile struct motionSegment motionBuffer[motionBuffer_length];  //stores all buffered moves

//  ----- CIRCULAR BUFFER INDEXES -----
//  When a new packet comes in, the write buffer position gets incremented and then that location is written to.
//  The main process detects that the write buffer is ahead of the read buffer, and increments the read buffer position
//  and then reads that location into the step generator.
volatile uint8_t motionBuffer_readPosition = 0; //gets incremented and then read, so reflects location that was last read
volatile uint8_t motionBuffer_writePosition = 0; //gets incremented and then written, so reflects location that was last written to.
volatile uint8_t motionBuffer_syncSearchPosition = 0; //the last buffer location where a search for a sync packet has been conducted.

//  ----- CONFIGURE URL -----
char myurl[] = "http://www.fabuint.com/vn/086-005b.py";

//  ----- USER SETUP -----
void userSetup(){
	// -- URL --
	setURL(&myurl[0], sizeof(myurl));

	// -- FABNET IO --
	IO_ledPORT = &PORTB; //FABNET LED
	IO_ledDDR = &DDRB;
	IO_ledPIN = &PINB;
	IO_ledPin = 1<<PB3;

	IO_buttonPORT = &PORTB; //FABNET BUTTON
	IO_buttonDDR = &DDRB;
	IO_buttonPIN = &PINB;
	IO_buttonPin = 1<<PB2;

	IO_txrxPORT = &PORTD; //FABNET TXRX
	IO_txrxDDR = &DDRD;
	IO_rxPin = 1<<PD0;
	IO_txPin = 1<<PD1;

	IO_txEnablePORT = &PORTD; //FABNET TX ENABLE
	IO_txEnableDDR = &DDRD;
	IO_txEnablePin = 1<<PD2;

	// -- CLOCK GEN INTERRUPT TIMING MEASUREMENT --
	DDRB |= (1<<PB4); //configure MISO as output
	PORTB &= ~(1<<PB4); //initialize LOW

	// -- CONFIGURE ADC --
	ADMUX = (0<<REFS1)|(1<<REFS0)|(0<<ADLAR)|(stepper1_vRef);   //AVcc Reference, Right Adjusted, Source is stepper1_vRef
	ADCSRA = (1<<ADEN)|(0<<ADSC)|(0<<ADATE)|(0<<ADIF)|(0<<ADIE)|(1<<ADPS2)|(1<<ADPS1)|(1<<ADPS0);  //Enable ADC, clock source is CLK/128

	// -- CONFIGURE STEPPER IO --
	stepper1_DDR |= (1<<stepper1_Step)|(1<<stepper1_Direction)|(1<<stepper1_Reset)|(1<<stepper1_MS1)|(1<<stepper1_MS0)|(1<<stepper1_Enable);  //set all motor pins to outputs
	stepper1_PORT |= (1<<stepper1_Reset)|(1<<stepper1_Enable)|(1<<stepper1_MS0)|(1<<stepper1_MS1); //start with motor disabled, not in reset, 1/16 stepping
	stepper1_PORT &= ~(1<<stepper1_Direction)|(1<<stepper1_Step); //dir in reverse, step low, (note ~)

	// -- CONFIGURE TIMER1 FOR STEP GENERATION --
	TCCR1A = (0<<COM1A1)|(0<<COM1A0)|(0<<COM1B1)|(0<<COM1B0)|(0<<WGM11)|(0<<WGM10);  //CTC on OCR1A
	TCCR1B = (0<<ICNC1)|(0<<ICES1)|(0<<WGM13)|(1<<WGM12)|(0<<CS12)|(0<<CS11)|(1<<CS10);  //CTC on OCR1A, CLK/1
	OCR1A = stepGenerator_timeBase;

	// -- INITIALIZE STATES --
	enableStepGenerator();
	resetAllDrivers();
	disableAllDrivers();
}

//  ----- LED UTILITY FUNCTIONS -----
void ledOn(){
	*IO_ledPORT |= IO_ledPin;
}

void ledOff(){
	*IO_ledPORT &= ~IO_ledPin;
}

//  ----- STEPPER UTILITY FUNCTIONS -----

void enableStepGenerator(){
	// Enables step generation
	TIMSK1 = (1<<OCIE1A);  //timer interrupt on
}

void disableStepGenerator(){
	// Disables step generation
	TIMSK1 = (0<<OCIE1A);  //timer interrupt on
}

void steppers_enterReset(){
	// Enters a reset state on all stepper drivers
	stepper1_PORT &= ~(1<<stepper1_Reset);
}

void steppers_exitReset(){
	// Exits a reset state on all stepper drivers
	stepper1_PORT |= (1<<stepper1_Reset);
}

void resetAllDrivers(){
	// Resets the state of all driver chips
	steppers_enterReset();
	_delay_us(1); //in reality only needs 400ns per datasheet.
	steppers_exitReset();
}

void stepper1_enableDriver(){
	// Enables the Stepper 1 driver
	stepper1_PORT &= ~(1<<stepper1_Enable); //active low
}

void stepper1_disableDriver(){
	// Disables the Stepper 1 driver
	stepper1_PORT |= (1<<stepper1_Enable); //active low
}

void disableAllDrivers(){
	// Disables all stepper drivers
	stepper1_disableDriver();
}

void enableAllDrivers(){
	// Enables all stepper drivers
	stepper1_enableDriver();
}

void stepper1_forward(){
	// Stepper 1 in the forwards direction
	stepper1_PORT |= (1<<stepper1_Direction);
}

void stepper1_reverse(){
	// Stepper 1 in the reverse direction
	stepper1_PORT &= ~(1<<stepper1_Direction);
}

void setStepDirection(uint8_t stepper, uint8_t direction){
	// Sets the directions of each stepper
	switch(stepper){
		case 0:
			if(direction == 0){
				stepper1_reverse();
			}else{
				stepper1_forward();
			}
			break;
	}
}

void step(uint8_t activeDrivers){
	// Takes a step on all bit-indexed active drivers
	// Although the current node is a single-axis stepper, this will make the code flexible for expansion

	// -- Step Lines High --
	if(activeDrivers & (1<<0)){ //stepper 1
		stepper1_PORT |= (1<<stepper1_Step);
	}
	// -- Hold --
	_delay_us(1); //mandatory 1us delay, per A4982 datasheet p6
	// -- Step Lines Low
	stepper1_PORT &= ~(1<<stepper1_Step); //clear the step line
}

uint16_t stepper1_readVRef(){
	//returns the Stepper 1 current reference voltage
	ADCSRA |= (1<<ADSC);  //start conversion
	while(ADCSRA & (1<<ADSC)){  //wait for conversion to complete
	}

	uint16_t ADCResult = ADC; //conversion result
	return ADCResult;
}


//  ----- RX/TX BUFFER READ/WRITE OPERATIONS -----

void writeTxBuffer_uint16(uint16_t value, uint8_t payloadIndex){
	//Loads a uint16_t into the transmit buffer
	uint8_t baseLocation = payloadLocation + payloadIndex;
	txBuffer[baseLocation] = value & 0xFF; //low byte
	txBuffer[baseLocation + 1] = (uint8_t)(value>>8); //high byte
}

void writeTxBuffer_uint24(uint32_t value, uint8_t payloadIndex){
	//Loads a uint24 (stored as a uint32_t) into the transmit buffer
	uint8_t baseLocation = payloadLocation + payloadIndex;
	txBuffer[baseLocation] = (uint8_t)(value & 0xFF);
	txBuffer[baseLocation + 1] = (uint8_t)((value & 0xFF00) >> 8);
	txBuffer[baseLocation + 2] = (uint8_t)((value & 0xFF0000) >> 16);
}

void writeTxBuffer_int24(int32_t value, uint8_t payloadIndex){
	//loads an int24 (stored as an int32_t) into the transmit buffer
	writeTxBuffer_uint24((uint32_t)value, payloadIndex); // because you can truncate twos-complement numbers, all we need to do
														 // is simply cast the value as an unsigned and treat as normal
}

uint32_t readRxBuffer_uint24(uint8_t payloadIndex){
	//reads a uint24 from the payload buffer, and returns as a uint32_t
	uint8_t baseLocation = payloadLocation + payloadIndex;
	uint32_t value = (uint32_t)rxBuffer[baseLocation];
	value += ((uint32_t)rxBuffer[baseLocation + 1])<<8;
	value += ((uint32_t)rxBuffer[baseLocation + 2])<<16;
	return value;
}

int32_t readRxBuffer_int24(uint8_t payloadIndex){
	//reads an int24 from the payload buffer, and returns as an int32_t
	uint32_t unsignedValue = readRxBuffer_uint24(payloadIndex);

	if(unsignedValue>=0x800000){ //number is negative
		unsignedValue += 0xFF000000;
	};

	return (int32_t)unsignedValue;
}


//  ----- MOTION BUFFER OPERATIONS -----

uint8_t advanceMotionBufferWriteHead(){
	// Advances the motion buffer write head.
	// Returns 1 if successful, or 0 if the buffer is full (write head collides with the read head)
	uint8_t newWritePosition = motionBuffer_writePosition + 1; //preliminarily advance the write head
	if(newWritePosition == motionBuffer_length){ //wrap
		newWritePosition = 0;
	}
	if(newWritePosition == motionBuffer_readPosition){ //buffer is full
		return 0; //write head doesn't advance, and returns 0 to indicate buffer is full
	}else{
		motionBuffer_writePosition = newWritePosition; //advance write head
		return 1;
	}
}

uint8_t loadSegmentIntoMotionBuffer(){
	// Loads a segment from the rxBuffer into the motion buffer
	// Returns 1 if successful, or 0 if the buffer is full.
	uint8_t newWritePosition = motionBuffer_writePosition + 1; //preliminarily advance the write head
	if(newWritePosition == motionBuffer_length){ //wrap
		newWritePosition = 0;
	}
	if(newWritePosition == motionBuffer_readPosition){ //buffer is full
		return 0; //write head doesn't advance, and returns 0 to indicate buffer is full
	}else{ //motion buffer write head was PRELIMINARILY advanced successfully

		//load all stepper motors into buffer
		uint8_t stepperIndex;
		uint8_t packetIndex = 0;
		for(stepperIndex = 0; stepperIndex < numberOfSteppersOnNode; stepperIndex++){ //load all steppers into buffer
			motionBuffer[newWritePosition].stepper_target[stepperIndex]= (readRxBuffer_int24(packetIndex))<<smoothingMicrosteppingBits; //shift over by the internal native resolution
			packetIndex += 3;
		}
		motionBuffer[newWritePosition].segmentTime = readRxBuffer_uint24(packetIndex);
		motionBuffer[newWritePosition].segmentKey = rxBuffer[payloadLocation+packetIndex + 3];
		motionBuffer[newWritePosition].absoluteMove = rxBuffer[payloadLocation+packetIndex + 4];
		motionBuffer[newWritePosition].waitForSync = rxBuffer[payloadLocation+packetIndex + 5];

		motionBuffer_writePosition = newWritePosition; // Advance the write head. Need to do this last, since it triggers a read in the step generator interrupt!
		return 1;
	}
}

uint8_t loadSegmentIntoStepGenerator(){
	// Loads a segment from the motion buffer into the step generator.
	// A load will occur if a) there is a segment available in the motion buffer, AND b) a synchronization is not needed.
	// Sets the global waitingForSync flag if a sync is needed on the next available motion segment
	// Returns 1 if a segment is loaded, or 0 if not.
	if(motionBuffer_readPosition == motionBuffer_writePosition){ //no new segment available
		return 0;
	}else{ //A new segment is available
		uint8_t newReadPosition = motionBuffer_readPosition + 1; //tentatively advance the read head
		if(newReadPosition == motionBuffer_length){ //wrap-around
			newReadPosition = 0;
		}
		if(motionBuffer[newReadPosition].waitForSync == 1){ //can't load segment, because waiting on a synchronization packet
			waitingForSync = 1; //raise global flag that waiting for sync
//			ledOn();
			return 0; //can't load segment
		}else{ //segment can be loaded. Go ahead!
			waitingForSync = 0; //clear wait-for-sync flag
//			ledOff();
			//Advance the sync search position if it is on the prior read position. By definition, if this segment has been loaded,
			//then it is no longer awaiting synchronization and we can indicate that it has already been synchronized.
			if(motionBuffer_syncSearchPosition == motionBuffer_readPosition){
				motionBuffer_syncSearchPosition = newReadPosition;
			}
			//Advance the read head
			motionBuffer_readPosition = newReadPosition;
			// LOAD SEGMENT!
			uint8_t stepperIndex;
			int32_t targetSteps; //working register
			// - Load Stepper State -
			for(stepperIndex = 0; stepperIndex < numberOfSteppersOnNode; stepperIndex++){ //iterate over all steppers
				targetSteps = motionBuffer[motionBuffer_readPosition].stepper_target[stepperIndex]; //load target steps from segment buffer
				if(motionBuffer[motionBuffer_readPosition].absoluteMove == 1){ //absolute move, so convert into relative move
					targetSteps -= stepperPositions[stepperIndex]; //convert into relative move
				}
				if(targetSteps>0){ //set directions of each motor
					setStepDirection(stepperIndex, 1);
					activeSegment_stepperStates[stepperIndex].direction = 1;
				}else{
					targetSteps = -targetSteps; //need to make sure targetSteps is positive
					setStepDirection(stepperIndex, 0);
					activeSegment_stepperStates[stepperIndex].direction = -1;
				}
				//load stepper state for each motor
				activeSegment_stepperStates[stepperIndex].targetSteps = (uint32_t)targetSteps;
				activeSegment_stepperStates[stepperIndex].stepsRemaining = (uint32_t)targetSteps;
				activeSegment_stepperStates[stepperIndex].bresenhamAccumulator = 0;
			}
			// - Load Segment Key -
			activeSegment_segmentKey = motionBuffer[motionBuffer_readPosition].segmentKey;

			// - Load Bresenham Parameters -
			activeSegment_bresenhamTriggerThreshold = (int32_t)(motionBuffer[motionBuffer_readPosition].segmentTime>>1); //bresenham threshold is half the segment time
			activeSegment_totalTime = motionBuffer[motionBuffer_readPosition].segmentTime; //used in bresenham algorithm
			// segment time should be loaded last, because this is what triggers the step generator to begin working again
			activeSegment_timeRemaining = motionBuffer[motionBuffer_readPosition].segmentTime;
			return 1;
		}
	}
}

//  ----- STATUS RESPONSE -----
void transmitStatus(uint8_t responsePort, uint8_t statusCode){
	// transmits the current status state of the node to a response port, including the provided statusCode parameter
	txBuffer[payloadLocation] = statusCode;
	txBuffer[payloadLocation + 1] = activeSegment_segmentKey;
	writeTxBuffer_uint24(activeSegment_timeRemaining, 2);
	txBuffer[payloadLocation + 5] = motionBuffer_readPosition;
	txBuffer[payloadLocation + 6] = motionBuffer_writePosition;
	transmitUnicastPacket(responsePort, 7); //transmit 7 payload bytes to the response port
}


//  ----- USER LOOP -----
void userLoop(){

}

//  ----- SERVICE ROUTINES -----
void svc_getVRef(){
	// returns the current reference voltage
	// scale is 0v -> Vcc, 0-> 1024
	writeTxBuffer_uint16(stepper1_readVRef(), 0); //load into payloadLocation + 0
	transmitUnicastPacket(gestaltPort_getVRef, 2);
}

void svc_enableDrivers(){
	// enables or disables all drivers
	if(rxBuffer[payloadLocation]){ //payload is non-zero, so interpret as True and enable drivers
		enableAllDrivers();
	}else{ //payload is zero, disable drivers
		disableAllDrivers();
	}
	transmitUnicastPacket(gestaltPort_enableDrivers, 0); //send an empty reply
}

void svc_stepRequest(){
	uint8_t success = loadSegmentIntoMotionBuffer(); //0 if buffer is full, 1 if successful
	transmitStatus(gestaltPort_stepRequest, success);
}

void svc_getPosition(){
	uint8_t stepperIndex = 0;
	uint8_t packetIndex = 0;
	for(stepperIndex = 0; stepperIndex < numberOfSteppersOnNode; stepperIndex++){ //return all stepper positions
		writeTxBuffer_int24((stepperPositions[stepperIndex]>>smoothingMicrosteppingBits), packetIndex);
		packetIndex += 3;
	}
	transmitUnicastPacket(gestaltPort_getPosition, packetIndex);
}

void svc_getStatus(){
	transmitStatus(gestaltPort_getStatus, 1);
}

void svc_sync(){
//	ledOn();
	// Inbound synchronization signal
//	ledOn();
	if(waitingForSync){
		TCNT1 = 0; //step generator is currently waiting on synchronization, so reset counter to synchronize clocks.
	}
	uint8_t newSyncSearchPosition = motionBuffer_syncSearchPosition;
	do{
		if (newSyncSearchPosition == motionBuffer_writePosition){   //have already searched to the current write position
		  motionBuffer_syncSearchPosition = newSyncSearchPosition; //record that have searched to here.
		  return;
		}
		newSyncSearchPosition++; //increment sync search position
		if (newSyncSearchPosition == motionBuffer_length){  //wrap-around
		  newSyncSearchPosition = 0;
		}
	}while(motionBuffer[newSyncSearchPosition].waitForSync != 1);
	motionBuffer_syncSearchPosition = newSyncSearchPosition; //commit changes to sync write position.
	motionBuffer[newSyncSearchPosition].waitForSync = 0; //move is now ready to be run
//	ledOff();
}

//  ----- USER PACKET ROUTER -----
void userPacketRouter(uint8_t destinationPort){
	switch(destinationPort){
		case gestaltPort_getVRef: //get current reference voltages
			svc_getVRef();
			break;
		case gestaltPort_enableDrivers: //enable drivers
			svc_enableDrivers();
			break;
		case gestaltPort_stepRequest: //motion request
			svc_stepRequest();
			break;
		case gestaltPort_getPosition: //absolute position request
			svc_getPosition();
			break;
		case gestaltPort_getStatus: //status request
			svc_getStatus();
			break;
		case gestaltPort_sync: //synchronization packet
			svc_sync();
			break;
	};
};

//  ----- STEP GENERATOR INTERRUPT ROUTINE -----
ISR(TIMER1_COMPA_vect){
	if(activeSegment_timeRemaining > 0){ //something to do!
		activeSegment_timeRemaining --; //decrement time remaining

		// determine stepping axes
		uint8_t stepMask = 0; //keeps track of steps to take
		uint8_t stepperIndex;
		for(stepperIndex = 0; stepperIndex < numberOfSteppersOnNode; stepperIndex++){
			activeSegment_stepperStates[stepperIndex].bresenhamAccumulator += activeSegment_stepperStates[stepperIndex].targetSteps;
			if(activeSegment_stepperStates[stepperIndex].bresenhamAccumulator > activeSegment_bresenhamTriggerThreshold){ //step triggered
				activeSegment_stepperStates[stepperIndex].bresenhamAccumulator -= activeSegment_totalTime; //subtract out total time of move for Bresenham algorithm
				stepMask += (1<<stepperIndex); //indicate that a step should be taken in this axis
				activeSegment_stepperStates[stepperIndex].stepsRemaining --;
				stepperPositions[stepperIndex] += activeSegment_stepperStates[stepperIndex].direction; //adjust absolute position
			}
		}
		step(stepMask); //take steps
	}
	if(activeSegment_timeRemaining == 0){ //waiting on a new packet. Note this could happen on the heels of a segment concluding, in the same interrupt call!
		if(loadSegmentIntoStepGenerator()==1){ //try to load a segment into the step generator
			enableAllDrivers();
		}
	}
}
