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
#define gestaltPort_sync			8 	// Triggers a sync. This is a proxy for the sync control line.
#define gestaltPort_setVRef 		11	// Sets current reference
#define gestaltPort_enableDrivers	12	// enables or disables stepper driver
#define gestaltPort_stepRequest		13  // steps a relative number of steps, or to an absolute position
#define gestaltPort_getPosition		14	// returns the current absolute position
#define gestaltPort_getStatus		15	// returns the current node status

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
	aMSDDR  |= (1<<aMS0)|(1<<aMS1);
	aMSPORT |= (1<<aMS0)|(1<<aMS1);  //initialize in 1/16th microstepping mode
	bMSDDR  |= (1<<bMS0)|(1<<bMS1);
	bMSPORT |= (1<<bMS0)|(1<<bMS1);  //initialize in 1/16th microstepping mode
	cMSDDR  |= (1<<cMS0)|(1<<cMS1);
	cMSPORT |= (1<<cMS0)|(1<<cMS1);  //initialize in 1/16th microstepping mode

	// -- STEP AND DIRECTION --
	aStepDDR  |= (1<<aStep);
	aDirDDR   |= (1<<aDir);
	bStepDDR  |= (1<<bStep);
	bDirDDR   |= (1<<bDir);
	cStepDDR  |= (1<<cStep);
	cDirDDR   |= (1<<cDir);

	// -- ENABLE --
	aEnableDDR |= (1<<aEnable);
	aEnablePORT |= (1<<aEnable); //initialize disabled
	bEnableDDR |= (1<<bEnable);
	bEnablePORT |= (1<<bEnable); //initialize disabled
	cEnableDDR |= (1<<cEnable);
	cEnablePORT |= (1<<cEnable); //initialize disabled

	// -- PWM --
	mosfetDDR |= (1<<mosfet); //set mosfet pin as output
	mosfetPORT &= ~(1<<mosfet); //initialize in off position
	TCCR0A = (1<<COM0A1)|(1<<WGM01)|(1<<WGM00); //fast pwm mode, non-inverted output on OC0A
	TCCR0B = (1<<CS02)|(0<<CS00)|(0<<CS01); //clk/8, pwm freq ~= 9kHz
	OCR0A = 0;
	TIMSK0 = 0;

	// -- SERVO --
	servoDDR |= (1<<servo);
	servoPORT &= ~(1<<servo);

	// -- CONFIGURE TWI FOR DIGITAL POTENTIOMETER --
	TWBR = 84;  //~100KHz
	TWSR = 0;   // sets prescalar bits to zero
	TWCR = 1<<TWEN; //enable TWI

	// -- CONFIGURE TIMER 1 FOR STEP GENERATION --
	TCCR1A = (0<<COM1A1)|(0<<COM1A0)|(0<<COM1B1)|(0<<COM1B0)|(0<<WGM11)|(0<<WGM10);  //CTC on OCR1A
	TCCR1B = (0<<ICNC1)|(0<<ICES1)|(0<<WGM13)|(1<<WGM12)|(0<<CS12)|(0<<CS11)|(1<<CS10);  //CTC on OCR1A, CLK/1
	OCR1A = 921 ;  //921 clock ticks per stepper routine, time unit = 50uS ~= 20KHz
	TIMSK1 = (1<<OCIE1A);  //timer interrupt on

	// -- INITIALIZE STATES --
	enableStepGenerator();
	resetAllDrivers();
	disableAllDrivers();

	//enable watchdog timer
	//mcu was getting into a weird state at times... hopefully this'll help recover to a useable state
	// wdt_enable(WDTO_120MS);
}

void userLoop(){
  // wdt_reset();
  // PINB |= (1<<PB1);
  // _delay_ms(20);
};



//----UTILITY FUNCTIONS----

//TWI FUNCTIONS

void waitForConfirmation(){
  uint16_t waitCounter = 0;
  while(!(TWCR&(1<<TWINT))){
    waitCounter++;  //this keeps the controller from hanging if TWI isn't functioning for some reason.
    if(waitCounter == 65000){
      return;
    }
  };
}

uint8_t TWIStartTransaction(){
  TWCR = (1<<TWINT)|(1<<TWSTA)|(1<<TWEN); //issue start pulse
  waitForConfirmation();
  if(TWSR != 0x08){
    return TWSR; //COULD NOT INITIATE TRANSMISSION
  }
  return 0; //start pulse sent successfully
}

uint8_t TWITransmitAddress(uint8_t SLA_W){
  TWDR = SLA_W;
  TWCR = (1<<TWINT)|(1<<TWEN);  //transmit address data
  waitForConfirmation();
  if(TWSR != 0x18){
    return TWSR; //RECEIVED A NACK (NOT ACKNOWLEDGED)
  }
  return 0; //address transmitted successfully
}

uint8_t TWITransmitByte(uint8_t data){
  TWDR = data;
  TWCR = (1<<TWINT)|(1<<TWEN);  //transmit data
  waitForConfirmation();
  if(TWSR != 0x28){
    return TWSR; //RECEIVED A NACK (NOT ACKNOWLEDGED)
  }
  return 0; //data byte transmitted successfully
}

void TWIEndTransaction(){
  TWCR = (1<<TWINT)|(1<<TWEN)|(1<<TWSTO); //sends stop condition
}


//SERVICE ROUTINES
void svcSetReferenceVoltages(){
  uint8_t result = 0;   //result stores the return value of various TWI calls. 0 indicates success
                        //other values should be looked up on p220 of atmega324 data sheet.

  uint8_t axis  =   rxBuffer[payloadLocation + vrefAxis];
  uint8_t value =   rxBuffer[payloadLocation + vrefValue];

  result = TWIStartTransaction();
  if(result){
    txBuffer[payloadLocation] = result;
    transmitUnicastPacket(vrefPort, 1);
    return;
  }

  result = TWITransmitAddress(0b01011110);  //sends a write command to digital potentiometer
  if(result){
    txBuffer[payloadLocation] = result;
    transmitUnicastPacket(vrefPort, 1);
    return;
  }

  switch(axis){
    case(0):  //x axis
      result = TWITransmitByte(0x10); //write to volatile wiper 1
      break;
    case(1):  //y axis
      result = TWITransmitByte(0x00); //write to volatile wiper 0
      break;
    case(2): //z axis
      result = TWITransmitByte(0x60); //write to volatile wiper 2
      break;
  }
  if(result){
    txBuffer[payloadLocation] = result;
    transmitUnicastPacket(vrefPort, 1);
    return;
  }

  result = TWITransmitByte(value);
  if(result){
    txBuffer[payloadLocation] = result;
    transmitUnicastPacket(vrefPort, 1);
    return;
  }

  TWIEndTransaction();

  txBuffer[payloadLocation] = 0;
  transmitUnicastPacket(vrefPort, 1);
}

void svcTest(){
  aEnablePORT &= ~(1<<aEnable);
  bEnablePORT &= ~(1<<bEnable);
  cEnablePORT &= ~(1<<cEnable);
  transmitUnicastPacket(testPort, 0);
  volatile uint16_t counter = 0;
  while(1){
    aStepPORT |= (1<<aStep);
    bStepPORT |= (1<<bStep);
    cStepPORT |= (1<<cStep);

    _delay_us(1);
    aStepPORT &= ~(1<<aStep);
    bStepPORT &= ~(1<<bStep);
    cStepPORT &= ~(1<<cStep);

    _delay_ms(1);
    counter ++;
    if (counter == 5000){
      break;
    }

  }
  aEnablePORT |= (1<<aEnable);
  bEnablePORT |= (1<<bEnable);
  cEnablePORT |= (1<<cEnable);
}

void svcMove(){
  uint8_t newWritePosition = writePosition + 1; //check for buffer full condition before overwriting buffer position
  if(newWritePosition==bufferLength){ //wrap-around
    newWritePosition = 0;
  }
  if(newWritePosition == readPosition){ //buffer full
    txBuffer[payloadLocation + statusCode] = 0;
    txBuffer[payloadLocation + statusCurrentKey] = moveBuffer[readPosition].segmentKey;
    txBuffer[payloadLocation + statusStepsRemaining] = majorStepsRemaining>>microstepping;
    txBuffer[payloadLocation + statusReadPosition] = readPosition;
    txBuffer[payloadLocation + statusWritePosition] = writePosition;
    transmitUnicastPacket(movePort, 5); //5 payload bytes in packet
    return;
  }

  //fill segment parameters
  segmentKeyCounter ++; //increment segment key counter before pulling a key
  moveBuffer[newWritePosition].segmentKey = segmentKeyCounter;
  moveBuffer[newWritePosition].majorSteps = rxBuffer[payloadLocation + moveMajorSteps];
  moveBuffer[newWritePosition].directions = rxBuffer[payloadLocation + moveDirections];
  moveBuffer[newWritePosition].aSteps = rxBuffer[payloadLocation + moveASteps];
  moveBuffer[newWritePosition].bSteps = rxBuffer[payloadLocation + moveBSteps];
  moveBuffer[newWritePosition].cSteps = rxBuffer[payloadLocation + moveCSteps];
  moveBuffer[newWritePosition].accel = rxBuffer[payloadLocation + moveAccel];
  moveBuffer[newWritePosition].accelSteps = rxBuffer[payloadLocation + moveAccelSteps];
  moveBuffer[newWritePosition].deccelSteps = rxBuffer[payloadLocation + moveDeccelSteps];

  //transmit a response
  txBuffer[payloadLocation + statusCode] = 1;
  txBuffer[payloadLocation + statusCurrentKey] = moveBuffer[readPosition].segmentKey;
  txBuffer[payloadLocation + statusStepsRemaining] = majorStepsRemaining>>microstepping;
  txBuffer[payloadLocation + statusReadPosition] = readPosition;
  txBuffer[payloadLocation + statusWritePosition] = newWritePosition;
  transmitUnicastPacket(movePort, 5); //5 payload bytes in packet

  //increment write buffer position (this will trigger a read if idle)
  writePosition = newWritePosition;
  return;
}

void svcSpinStatus(){
  //transmit a response
  txBuffer[payloadLocation + statusCode] = 1;
  txBuffer[payloadLocation + statusCurrentKey] = moveBuffer[readPosition].segmentKey;
  txBuffer[payloadLocation + statusStepsRemaining] = majorStepsRemaining>>microstepping;
  txBuffer[payloadLocation + statusReadPosition] = readPosition;
  txBuffer[payloadLocation + statusWritePosition] = writePosition;
  transmitUnicastPacket(spinStatusPort, 5); //5 payload bytes in packet
}

void svcDisableMotors(){
  aEnablePORT |= (1<<aEnable);
  bEnablePORT |= (1<<bEnable);
  cEnablePORT |= (1<<cEnable);
  transmitUnicastPacket(disableMotorsPort, 0);
}

void svcPWM(){
  OCR0A = rxBuffer[payloadLocation];
  txBuffer[payloadLocation] = OCR0A;
  transmitUnicastPacket(pwmPort, 1);
  return;
}

//PACKET ROUTER
void userPacketRouter(uint8_t destinationPort){
  switch(destinationPort){
    case vrefPort: //enable drivers request
      svcSetReferenceVoltages();
      break;
    case testPort:
      svcTest();
      break;
    case movePort:
      svcMove();
      break;
    case spinStatusPort:
      svcSpinStatus();
      break;
    case disableMotorsPort:
      svcDisableMotors();
      break;
    case pwmPort:
      svcPWM();
      break;
  }
};

//-----INTERRUPT ROUTINES------

//STEP GENERATOR
ISR(TIMER1_COMPA_vect){
  //check for steps to move
  if(majorStepsRemaining>0){

    //ACCEL/DECCEL
    if(accelSteps > (majorSteps-majorStepsRemaining)){  //accelerating, changed from >= to >, should examine implications more
      uVelocity += uAccel;  //accelerate
    }else if(deccelSteps >= majorStepsRemaining){  //deccelerating
      if (uVelocity > uAccel){ //make sure not to go negative
        uVelocity -= uAccel;  //deccelerate
      }else{
        uVelocity = 0;
      }
    }

    //MODIFY uPOSITION
    uPosition += uVelocity;

    //MAJOR AXIS STEP AND BRESENHAM ALGORITHM
    if(uPosition>uSteps){
      majorStepsRemaining --; //take a step in the virtual major axis
      uPosition -= uSteps;

      aError += aSteps;
      bError += bSteps;
      cError += cSteps;

      if(aError > int16_t(majorError)){ //take step in A
        aStepPORT |= (1<<aStep);
        aError -= int16_t(majorSteps);
      }
      if(bError > int16_t(majorError)){ //take step in B
        bStepPORT |= (1<<bStep);
        bError -= int16_t(majorSteps);
      }
      if(cError > int16_t(majorError)){ //take step in C
        cStepPORT |= (1<<cStep);
        cError -= int16_t(majorSteps);
      }
      _delay_us(1);

      aStepPORT &= ~(1<<aStep); //clear all step lines
      bStepPORT &= ~(1<<bStep);
      cStepPORT &= ~(1<<cStep);

    }

  }else{  //check for new packet to load
      if(writePosition!=readPosition){
        // ENABLE AXES
        aEnablePORT &= ~(1<<aEnable);
        bEnablePORT &= ~(1<<bEnable);
        cEnablePORT &= ~(1<<cEnable);
        readPosition ++;
        if(readPosition == bufferLength){ //wrap-around
          readPosition = 0;
        }

        //LOAD MAJOR STEP VARIABLES
        majorSteps = uint16_t(moveBuffer[readPosition].majorSteps)<<microstepping;
        majorError = majorSteps>>1;
        majorStepsRemaining = majorSteps;

        //SET MOTOR DIRECTIONS
        if(moveBuffer[readPosition].directions & aDirectionMask){
          aDirPORT   |= (1<<aDir);
        }else{
          aDirPORT   &= ~(1<<aDir);
        }
        if(moveBuffer[readPosition].directions & bDirectionMask){
          bDirPORT   |= (1<<bDir);
        }else{
          bDirPORT   &= ~(1<<bDir);
        }
        if(moveBuffer[readPosition].directions & cDirectionMask){
          cDirPORT   |= (1<<cDir);
        }else{
          cDirPORT   &= ~(1<<cDir);
        }

        //SET AXIS STEPS
        aSteps = int16_t(uint16_t(moveBuffer[readPosition].aSteps)<<microstepping);
        bSteps = int16_t(uint16_t(moveBuffer[readPosition].bSteps)<<microstepping);
        cSteps = int16_t(uint16_t(moveBuffer[readPosition].cSteps)<<microstepping);
        aError = 0;
        bError = 0;
        cError = 0;

        //SET ACCEL/DECCEL PARAMETERS
        //FIX BY UNCOMMENTING LINES
//        accelSteps = (uint16_t(moveBuffer[readPosition].accelSteps)<<microstepping);
//        deccelSteps = (uint16_t(moveBuffer[readPosition].deccelSteps)<<microstepping);
//        uAccel = (uint16_t(moveBuffer[readPosition].accel)<<microstepping);  //might need to shift here by microstepping. Remember that accel is per cycle, not step.

        //CLEAR uPOSITION
        uPosition = 0; //this way acceleration will be more consistent in the face of rounding errors.
      }
  }
}
