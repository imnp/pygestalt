//  096 Magic Mill: Motion Controller
//  A Gestalt Node
//
// (C) 2013 Ilan E. Moyer and MIT CADLAB
//
//--REVISION HISTORY--------------
//  --------------------------------------------------------------------------------------------------------
//  | DATE    | MODIFICATIONS                            | NAME              | FILENAME                    |
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |03/15/13 | CREATED                                  | ILAN E. MOYER     | 096-001a.cpp                |
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |03/02/20 | UPDATED FOR PYGESTALT 0.7                | ILAN E. MOYER     | 096-001b.cpp                |
//  --------------------------------------------------------------------------------------------------------
//
// 	NOTE: 	In version B, the stepper-related functions, including loading, processing, and executing motion segments, are
//			based off of the firmware for the networked stepper driver 086-005b. This is a good test of how easily it scales
//			with multiple axes.

// ----- INCLUDES -----
#include <gestalt.h>
#include <avr/io.h>
#include <stdlib.h>
#include <math.h>
#include <util/delay.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>

//  ----- HEADERS -----
void enableStepGenerator();
void disableStepGenerator();
void steppers_enterReset();
void steppers_exitReset();
void resetAllDrivers();
void stepperA_enableDriver();
void stepperA_disableDriver();
void stepperB_enableDriver();
void stepperB_disableDriver();
void stepperC_enableDriver();
void stepperC_disableDriver();
void disableAllDrivers();
void enableAllDrivers();
void stepperA_forward();
void stepperA_reverse();
void stepperB_forward();
void stepperB_reverse();
void stepperC_forward();
void stepperC_reverse();


//  ----- IO DEFINITIONS -----
//  -- STEPPER A --
#define stepperA_MS_PORT     PORTC
#define stepperA_MS_DDR      DDRC
#define stepperA_MS0 		 PC5
#define stepperA_MS1         PC4

#define stepperA_Step_PORT   PORTC
#define stepperA_Step_DDR    DDRC
#define stepperA_Step        PC3

#define stepperA_Dir_PORT    PORTC
#define stepperA_Dir_DDR     DDRC
#define stepperA_Dir         PC2

#define stepperA_Enable_PORT PORTC
#define stepperA_Enable_DDR  DDRC
#define stepperA_Enable      PC6

//  -- STEPPER B --
#define stepperB_MS_PORT     PORTA
#define stepperB_MS_DDR      DDRA
#define stepperB_MS0         PA5
#define stepperB_MS1         PA6

#define stepperB_Step_PORT   PORTA
#define stepperB_Step_DDR    DDRA
#define stepperB_Step        PA7

#define stepperB_Dir_PORT    PORTC
#define stepperB_Dir_DDR     DDRC
#define stepperB_Dir         PC7

#define stepperB_Enable_PORT PORTA
#define stepperB_Enable_DDR  DDRA
#define stepperB_Enable      PA4

//  -- STEPPER C --
#define stepperC_MS_PORT     PORTA
#define stepperC_MS_DDR      DDRA
#define stepperC_MS0         PA0
#define stepperC_MS1         PA1

#define stepperC_Step_PORT   PORTA
#define stepperC_Step_DDR    DDRA
#define stepperC_Step        PA2

#define stepperC_Dir_PORT    PORTA
#define stepperC_Dir_DDR     DDRA
#define stepperC_Dir         PA3

#define stepperC_Enable_PORT PORTB
#define stepperC_Enable_DDR  DDRB
#define stepperC_Enable      PB0

//  -- MOSFET --
#define mosfet_PORT  PORTB
#define mosfet_DDR   DDRB
#define mosfet	     PB3

//  -- SERVO --
#define servo_PORT   PORTB
#define servo_DDR    DDRB
#define servo        PB1

//  -- POTENTIOMETER --
#define potentiometer_PORT    PORTD
#define potentiometer_DDR     DDRD
#define potentiometer         PD7


//  ----- GESTALT PORT DEFINITIONS -----
#define gestaltPort_setVRef 		11	// Sets current reference
#define gestaltPort_enableDrivers	12	// enables or disables stepper driver
#define gestaltPort_stepRequest		13  // steps a relative number of steps, or to an absolute position
#define gestaltPort_getPosition		14	// returns the current absolute position
#define gestaltPort_getStatus		15	// returns the current node status
#define gestaltPort_PWM				16  // Adjusts the output of the PWM MOSFET driver

//  ----- STEPPING PARAMETERS -----
#define defaultHardwareMicrostepping		3	// 0b00: Full, 0b01: Half, 0b10: Quarter, 0b11: Sixteenth -- NOTE: this is set manually on a per-bit basis in userSetup()
#define smoothingMicrosteppingBits			2   // The number of bits of microstepping used purely for smoothing. The positioning step resolution is quarter-steps.
#define numberOfSteppersOnNode				3 	// Three steppers on the node

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
struct motionSegment{ //19 bytes
  volatile int32_t stepper_target[numberOfSteppersOnNode]; //either target number of steps, or target absolute position
  volatile uint32_t segmentTime; //execution time of the segment, in motion ticks (units of 62.5us)
  volatile uint8_t segmentKey; //a rolling key counter that identifies the active segment
  volatile uint8_t absoluteMove; //0: incremental, 1: absolute
  volatile uint8_t waitForSync; //0: cleared to run this segment, 1: wait for synchronization signal
};

const uint8_t motionBuffer_length = 32;  //608 bytes, on an atmega32x total memory is 2K. This is approximately 0.75 seconds of move data with one node on network.
volatile struct motionSegment motionBuffer[motionBuffer_length];  //stores all buffered moves

//  CIRCULAR BUFFER INDEXES
//  When a new packet comes in, the write buffer position gets incremented and then that location is written to.
//  The main process detects that the write buffer is ahead of the read buffer, and increments the read buffer position
//  and then reads that location into the step generator.
volatile uint8_t motionBuffer_readPosition = 0; //gets incremented and then read, so reflects location that was last read
volatile uint8_t motionBuffer_writePosition = 0; //gets incremented and then written, so reflects location that was last written to.
volatile uint8_t motionBuffer_syncSearchPosition = 0; //the last buffer location where a search for a sync packet has been conducted.

//  ----- CONFIGURE URL -----
char myurl[] = "http://www.fabuint.com/vn/096-001b.py";


//  ----- USER SETUP -----
void userSetup(){
	// -- URL
	setURL(&myurl[0], sizeof(myurl));

	// -- FABNET IO --
	IO_ledPORT = &PORTB;
	IO_ledDDR = &DDRB;
	IO_ledPIN = &PINB;
	IO_ledPin = 1<<4;   //note that this is a dummy, no led is on the current rev of the board.
						//although it would be cool to include a side-firing led in a future rev.

	IO_txrxPORT = &PORTD;
	IO_txrxDDR = &DDRD;
	IO_rxPin = 1<<0;  //PD0
	IO_txPin = 1<<1;  //PD1

	// -- MICROSTEPPING --
	stepperA_MS_DDR  |= (1<<stepperA_MS0)|(1<<stepperA_MS1);
	stepperA_MS_PORT |= (1<<stepperA_MS0)|(1<<stepperA_MS1);  //initialize in 1/16th microstepping mode
	stepperB_MS_DDR  |= (1<<stepperB_MS0)|(1<<stepperB_MS1);
	stepperB_MS_PORT |= (1<<stepperB_MS0)|(1<<stepperB_MS1);  //initialize in 1/16th microstepping mode
	stepperC_MS_DDR  |= (1<<stepperC_MS0)|(1<<stepperC_MS1);
	stepperC_MS_PORT |= (1<<stepperC_MS0)|(1<<stepperC_MS1);  //initialize in 1/16th microstepping mode

	// -- STEP AND DIRECTION --
	stepperA_Step_DDR  |= (1<<stepperA_Step);
	stepperA_Dir_DDR   |= (1<<stepperA_Dir);
	stepperB_Step_DDR  |= (1<<stepperB_Step);
	stepperB_Dir_DDR   |= (1<<stepperB_Dir);
	stepperC_Step_DDR  |= (1<<stepperC_Step);
	stepperC_Dir_DDR   |= (1<<stepperC_Dir);

	// -- ENABLE --
	stepperA_Enable_DDR |= (1<<stepperA_Enable);
	stepperB_Enable_DDR |= (1<<stepperB_Enable);
	stepperC_Enable_DDR |= (1<<stepperC_Enable);

	// -- PWM --
	mosfet_DDR |= (1<<mosfet); //set mosfet pin as output
	mosfet_PORT &= ~(1<<mosfet); //initialize in off position
	TCCR0A = (1<<COM0A1)|(1<<WGM01)|(1<<WGM00); //fast pwm mode, non-inverted output on OC0A
	TCCR0B = (1<<CS02)|(0<<CS00)|(0<<CS01); //clk/8, pwm freq ~= 9kHz
	OCR0A = 0;
	TIMSK0 = 0;

	// -- SERVO --
	servo_DDR |= (1<<servo);
	servo_PORT &= ~(1<<servo);

	// -- CONFIGURE TWI FOR DIGITAL POTENTIOMETER --
	TWBR = 84;  //~100KHz
	TWSR = 0;   // sets prescalar bits to zero
	TWCR = 1<<TWEN; //enable TWI

	// -- CONFIGURE TIMER1 FOR STEP GENERATION --
	TCCR1A = (0<<COM1A1)|(0<<COM1A0)|(0<<COM1B1)|(0<<COM1B0)|(0<<WGM11)|(0<<WGM10);  //CTC on OCR1A
	TCCR1B = (0<<ICNC1)|(0<<ICES1)|(0<<WGM13)|(1<<WGM12)|(0<<CS12)|(0<<CS11)|(1<<CS10);  //CTC on OCR1A, CLK/1
	OCR1A = stepGenerator_timeBase;

	// -- INITIALIZE STATES --
	enableStepGenerator();
	resetAllDrivers();
	disableAllDrivers();

	//enable watchdog timer
	//mcu was getting into a weird state at times... hopefully this'll help recover to a useable state
	// wdt_enable(WDTO_120MS);
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
	// Not supported at the moment
}

void steppers_exitReset(){
	// Exits a reset state on all stepper drivers
	// not supported at the moment
}

void resetAllDrivers(){
	// Resets the state of all driver chips
	steppers_enterReset();
	_delay_us(1); //in reality only needs 400ns per datasheet.
	steppers_exitReset();
}


void disableAllDrivers(){
	// Disables all stepper drivers
	stepperA_Enable_PORT |= (1<<stepperA_Enable);
	stepperB_Enable_PORT |= (1<<stepperB_Enable);
	stepperC_Enable_PORT |= (1<<stepperC_Enable);
}

void enableAllDrivers(){
	// Enables all stepper drivers
	stepperA_Enable_PORT &= ~(1<<stepperA_Enable);
	stepperB_Enable_PORT &= ~(1<<stepperB_Enable);
	stepperC_Enable_PORT &= ~(1<<stepperC_Enable);
}

void setStepDirection(uint8_t stepper, uint8_t direction){
	// Sets the directions of each stepper
	switch(stepper){
		case 0: // stepper A
			if(direction == 0){
				stepperA_Dir_PORT &= ~(1<<stepperA_Dir); // stepper A: reverse
			}else{
				stepperA_Dir_PORT |= (1<<stepperA_Dir); // stepper A: forward
			}
			break;
		case 1: // stepper B
			if(direction == 0){
				stepperB_Dir_PORT &= ~(1<<stepperB_Dir); // stepper B: reverse
			}else{
				stepperB_Dir_PORT |= (1<<stepperB_Dir); // stepper B: forward
			}
			break;
		case 2: // stepper C
			if(direction == 0){
				stepperC_Dir_PORT &= ~(1<<stepperC_Dir); // stepper C: reverse
			}else{
				stepperC_Dir_PORT |= (1<<stepperC_Dir); // stepper C: forward
			}
			break;
	}
}

void step(uint8_t activeDrivers){
	// Takes a step on all bit-indexed active drivers
	// Although the current node is a single-axis stepper, this will make the code flexible for expansion

	// -- Step Lines High --
	if(activeDrivers & (1<<0)){ //stepper A
		stepperA_Step_PORT |= (1<<stepperA_Step);
	}

	if(activeDrivers & (1<<1)){ //stepper B
		stepperB_Step_PORT |= (1<<stepperB_Step);
	}

	if(activeDrivers & (1<<2)){ //stepper C
		stepperC_Step_PORT |= (1<<stepperC_Step);
	}

	// -- Hold --
	_delay_us(1); //mandatory 1us delay, per A4982 datasheet p6
	// -- Step Lines Low
	stepperA_Step_PORT &= ~(1<<stepperA_Step); //clear the step lines
	stepperB_Step_PORT &= ~(1<<stepperB_Step);
	stepperC_Step_PORT &= ~(1<<stepperC_Step);
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

//  -- TWI FUNCTIONS --

void TWI_waitForConfirmation(){
  uint16_t waitCounter = 0;
  while(!(TWCR&(1<<TWINT))){
    waitCounter++;  //this keeps the controller from hanging if TWI isn't functioning for some reason.
    if(waitCounter == 65000){
      return;
    }
  };
}

uint8_t TWI_startTransaction(){
  TWCR = (1<<TWINT)|(1<<TWSTA)|(1<<TWEN); //issue start pulse
  TWI_waitForConfirmation();
  if(TWSR != 0x08){
    return TWSR; //COULD NOT INITIATE TRANSMISSION
  }
  return 0; //start pulse sent successfully
}

uint8_t TWI_transmitAddress(uint8_t SLA_W){
  TWDR = SLA_W;
  TWCR = (1<<TWINT)|(1<<TWEN);  //transmit address data
  TWI_waitForConfirmation();
  if(TWSR != 0x18){
    return TWSR; //RECEIVED A NACK (NOT ACKNOWLEDGED)
  }
  return 0; //address transmitted successfully
}

uint8_t TWI_transmitByte(uint8_t data){
  TWDR = data;
  TWCR = (1<<TWINT)|(1<<TWEN);  //transmit data
  TWI_waitForConfirmation();
  if(TWSR != 0x28){
    return TWSR; //RECEIVED A NACK (NOT ACKNOWLEDGED)
  }
  return 0; //data byte transmitted successfully
}

void TWI_endTransaction(){
  TWCR = (1<<TWINT)|(1<<TWEN)|(1<<TWSTO); //sends stop condition
}

// ----- USER LOOP -----
void userLoop(){
  // wdt_reset();
  // PINB |= (1<<PB1);
  // _delay_ms(20);
};

// ----- SERVICE ROUTINES -----
void svc_setReferenceVoltages(){
  uint8_t result = 0;   //result stores the return value of various TWI calls. 0 indicates success
                        //other values should be looked up on p220 of atmega324 data sheet.

  uint8_t axis  =   rxBuffer[payloadLocation]; // the axis on which to set the reference voltage
  uint8_t value =   rxBuffer[payloadLocation + 1]; //the potentiometer setting

  result = TWI_startTransaction();
  if(result){
    txBuffer[payloadLocation] = result;
    transmitUnicastPacket(gestaltPort_setVRef, 1);
    return;
  }

  result = TWI_transmitAddress(0b01011110);  //sends a write command to digital potentiometer
  if(result){
    txBuffer[payloadLocation] = result;
    transmitUnicastPacket(gestaltPort_setVRef, 1);
    return;
  }

  switch(axis){
    case(0):  //x axis
      result = TWI_transmitByte(0x10); //write to volatile wiper 1
      break;
    case(1):  //y axis
      result = TWI_transmitByte(0x00); //write to volatile wiper 0
      break;
    case(2): //z axis
      result = TWI_transmitByte(0x60); //write to volatile wiper 2
      break;
  }
  if(result){
    txBuffer[payloadLocation] = result;
    transmitUnicastPacket(gestaltPort_setVRef, 1);
    return;
  }

  result = TWI_transmitByte(value);
  if(result){
    txBuffer[payloadLocation] = result;
    transmitUnicastPacket(gestaltPort_setVRef, 1);
    return;
  }

  TWI_endTransaction();

  txBuffer[payloadLocation] = 0;
  transmitUnicastPacket(gestaltPort_setVRef, 1);
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


void svc_PWM(){
  OCR0A = rxBuffer[payloadLocation];
  txBuffer[payloadLocation] = OCR0A;
  transmitUnicastPacket(gestaltPort_PWM, 1);
  return;
}

//  ----- USER PACKET ROUTER -----
void userPacketRouter(uint8_t destinationPort){
	switch(destinationPort){
		case gestaltPort_setVRef: //get current reference voltages
			svc_setReferenceVoltages();
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
