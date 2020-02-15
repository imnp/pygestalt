# The Standard Gestalt Firmware Makefile
# Initial Revision: 3/1/2013
# Annotated on 4/7/2019
# Ilan Moyer and Nadya Peek
# www.pygestalt.org

## --- KEY PARAMETERS ---

# --- NAME OF MAIN C++ PROJECT ---
# Do not include extension, as assumes .cpp
PROJECT = 086-005b

# --- MICROCONTROLLER ---
MCU = atmega328p

# --- CLOCK FREQUENCY (in Hz) ---
FREQ = 18432000	

# --- START ADDRESS ---
# Comment out all but one of the below:

#  -> Use for application code
ADDRESS = 0x0000

#  -> Use for bootloader
#ADDRESS = 0x7000

# --- BUILD DEFINITIONS ---
# -DstandardGestalt : This should always be defined when using makefile. If not defined, Arduino is assumed.
# -Dbootloader: Build the bootloader
# -DnetworkedGestalt: Node is networked (thus utilizing an additional RS-485 control pin.)
# -Dgestalt324: Build for an Atmega324 (which has different interrupt names)
# -Dgestalt328: More of a note-to-self, as is default and has no actual effect on building.
# -DcompileLite: Build for smaller MCUs (e.g. Atmega168), which have a smaller bootloader area.

# Comment out all but one of the below:
#  -> Use for a networked Gestalt node application
GESTALT_DEFS = -DstandardGestalt -DnetworkedGestalt -Dgestalt328

#  -> Use below for a networked Gestalt node bootloader
#GESTALT_DEFS = -DstandardGestalt -Dbootloader -DnetworkedGestalt -Dgestalt328

#  -> Use below for a non-networked Gestalt node application
#GESTALT_DEFS = -DstandardGestalt -Dgestalt328

#  -> Use below for a non-networked Gestalt node bootloader
#GESTALT_DEFS = -DstandardGestalt -Dbootloader -Dgestalt328


# --- ABSOLUTE PATH OF gestalt.cpp LIBRARY ---
GESTALT_DIR = /users/imoyer/gsArduino


## --- COLLATE BUILD OPTION STRINGS ---
GESTALT_FILE = $(GESTALT_DIR)/gestalt.cpp
LDSECTION = --section-start=.text=$(ADDRESS)
SOURCES = $(PROJECT).cpp $(GESTALT_FILE)

CFLAGS = -g -Wall -Os -mmcu=$(MCU) -DF_CPU=$(FREQ) -I$(GESTALT_DIR) $(GESTALT_DEFS)
LDFLAGS = -Wl,$(LDSECTION)

## --- DEFAULT BEHAVIOR WHEN CALLING MAKE ---
# Build and clean:
all: $(PROJECT).hex clean

## --- INTERNAL BUILD PROCESS ---
#Build object files from source
$(PROJECT).o: $(SOURCES)
	avr-g++ $(CFLAGS) -c -Wall $(SOURCES)

#build executable and linker file from object files
$(PROJECT).elf: $(PROJECT).o
	avr-g++ $(CFLAGS) $(LDFLAGS) gestalt.o -o $@ $^

#Convert linker file into hex file, and display resource requirements
$(PROJECT).hex: $(PROJECT).elf
	avr-objcopy -j .text -j .data -O ihex $< $@
	avr-size -C --mcu=$(MCU) $(PROJECT).elf

## --- ADDITIONAL COMMAND LINE OPTIONS ---
# Remove all intermediate files
clean:
	rm -rf *.o *.elf

# Remove all built files
clean-all:
	rm -rf *.o *.elf $(PROJECT).hex	
	
# Flash using the Universal Personality Programmer (UPP)
flash:
	python UPPloader.py $(PROJECT).hex
	
# Build and load onto microcontroller
# Note that this is typically only used when flashing the bootloader onto the
# microcontroller, as application code can be loaded directly from the virtual node 
# via the bootloader.

load: $(PROJECT).hex flash clean
