## The Standard Gestalt Makefile

_Makefiles_ are necessary in order to compile firmware into a .hex file that can be loaded onto the physical node's microcontroller. Makefiles are essentially a recipe instructing the compiler how to build a .hex file from an input C++ file.

We have created a "standard" makefile that can be used to compile your Gestalt code. Because makefiles are inherently confusing, we'll step you thru our [standard makefile](https://github.com/imnp/pygestalt/tree/master/examples/standardMakefile) here.

### Key Parameters
The makefile is divided into roughly three sections. The first is where you will define a bunch of parameters that control how your code is compiled.

This is where you provide the name of your node's main C++ file. Leave off the extension; we assume it ends in .cpp:
```make
PROJECT = projectName
```

Defines the microcontroller type. This is needed by the AVR-GCC compiler in order to map register definitions correctly. A list of options is avaliable on the [AVR-GCC website](https://www.nongnu.org/avr-libc/user-manual/using_tools.html):
```make
MCU = atmega328p
```

The clock frequency, in Hz. This is required for time-based macros like _\_delay\_us()_ to accurately function:
```make
FREQ = 18432000	
```

The starting memory address of the compiled code. Use the above if you are compiling a standard node application:
```make
ADDRESS = 0x0000
```

Or, use the above INSTEAD if you are compiling a bootloader. This is valid for the Atmega 328 and 324. If you are compiling for a microcontroller with a different sized memory (e.g. the Atmega 168), you'll need to check the correct starting memory address for the bootloader section:

```make
ADDRESS = 0x7000
```

Here we are defining a bunch of flags that alter the functionality of the code by affecting which lines are compiled:

```make
GESTALT_DEFS = -DstandardGestalt -DnetworkedGestalt -Dgestalt328
```
The following flags are supported by the Gestalt firmware library:
- \-DstandardGestalt: This should always be defined when using makefile. If not defined, Arduino is assumed.
- \-Dbootloader: Will build a bootloader. This causes certain additional service routines to be included in the code.
- \-DnetworkedGestalt: This tells the compiler that the node is networked. The effect is to activate an additional control pin necessary for RS-485 communication.
- \-Dgestalt324: Builds for the Atmega324, which has different interrupt names.
- \-Dgestalt328: You'll see this in some makefiles, but it's just a "note-to-self" of sorts, as it doesn't actually do anything.
- \-DcompileLite: Build for smaller MCUs (e.g. Atmega168), which have a smaller bootloader area.

The makefile includes all of the following options. You should comment out all except the one you want, or modify to taste:

```make
#  -> Use for a networked Gestalt node application
GESTALT_DEFS = -DstandardGestalt -DnetworkedGestalt -Dgestalt328

#  -> Use below for a networked Gestalt node bootloader
GESTALT_DEFS = -DstandardGestalt -Dbootloader -DnetworkedGestalt -Dgestalt328

#  -> Use below for a non-networked Gestalt node application
GESTALT_DEFS = -DstandardGestalt -Dgestalt328

#  -> Use below for a non-networked Gestalt node bootloader
GESTALT_DEFS = -DstandardGestalt -Dbootloader -Dgestalt328
```

Lastly, we'll tell the compiler where it can find the Gestalt firmware library (gestalt.cpp and gestalt.h). You should change this to match where you've installed (or symlinked) the Gestalt library.

```make
GESTALT_DIR = users/imoyer/gsArduino
```

### Collate Build Option Strings
Here the makefile is just taking the options above and putting them into the format needed by the compiler and linker.

This builds up the absolute path of the Gestalt library:
```make
GESTALT_FILE = $(GESTALT_DIR)/gestalt.cpp
```

Tells the linker where the code section starts:
```make
LDSECTION = --section-start=.text=$(ADDRESS)
```

Builds a list of the primary source files needed to compile:
```make
SOURCES = $(PROJECT).cpp $(GESTALT_FILE)
```

Collates all compiler flags:
```make
CFLAGS = -g -Wall -Os -mmcu=$(MCU) -DF_CPU=$(FREQ) -I$(GESTALT_DIR) $(GESTALT_DEFS)
```

Collates all linker flags:
```make
LDFLAGS = -Wl,$(LDSECTION)
```

### Default Behavior When Calling Make

The following line builds the project and then deletes all intermediate files. This ideally would be in the next section after all of the avr-g++ calls, but for whatever reason this causes the compilation process to stop prematurely:

```make
all: $(PROJECT).hex clean
```

This is the default behavior, and can be evoked simply by running make.

```bash
>> make
```

### Internal Build Process
Builds an object file from the source code:
```make
$(PROJECT).o: $(SOURCES)
	avr-g++ $(CFLAGS) -c -Wall $(SOURCES)
```

Builds an executable and linkable format (ELF) file from the object file:
```make
$(PROJECT).elf: $(PROJECT).o
	avr-g++ $(CFLAGS) $(LDFLAGS) gestalt.o -o $@ $^
```

Converts the ELF file into a hex file:
```make
$(PROJECT).hex: $(PROJECT).elf
	avr-objcopy -j .text -j .data -O ihex $< $@
```

### Additional Command Line Options
The following additional lines in the makefile define options you can invoke from the terminal. Each is presented first as the makefile line, and then the corresponding terminal command.

Deletes all intermediate files created in the build process:
```make
clean:
	rm -rf *.o *.elf
```

In the terminal:
```bash
>> make clean
```

Deletes _ALL_ files created in the build process. This is typically used in conjuncture with a programmer:

```make
clean-all:
	rm -rf *.o *.elf $(PROJECT).hex
```

In the terminal:
```bash
>> make clean-all
```

The following builds the code and then programs the target microcontroller using the Universal Personality Programmer. You can alternatively replace the line with the terminal command for avrdude, etc...
```make
flash:
	python UPPloader.py $(PROJECT).hex
```

In the terminal:
```bash
>> make flash
```

This will build the code, program the microcontroller, and then delete all of the built files:

```make
load: $(PROJECT).hex flash clean
```

In the terminal:
```bash
>> make load
```

It is worth noting that typically we only use this command when flashing a Gestalt bootloader onto a fresh microcontroller. Application code can be more easily loaded onto the MCU via the virtual node bootloader functions.