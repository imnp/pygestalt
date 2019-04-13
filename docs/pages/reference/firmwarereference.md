## Gestalt Firmware Library Reference
### Reserved Microcontroller Resources

#### Memory Resources
- SRAM: 640 bytes. This leaves 1408 bytes remaining on an Atmega328.
- EEPROM: Addresses 0, 1 and 2.
- Program Memory: 2250 bytes. Approx 7% of avaliable on Atmega328.

#### I/O
- USART0 Tx and Rx pins. PD0 and PD1 on Atmega328.
- Networked Gestalt: three pins for an LED, pushbutton, and transciever enable. These are user-assignable.

#### Peripherals
- USART0 (Universal Serial Tranceiver 0)
- Timer2: used as a watchdog timer for receiver
